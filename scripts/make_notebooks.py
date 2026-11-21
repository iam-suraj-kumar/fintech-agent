"""Generate the Fraud Guard walkthrough notebooks into <repo>/notebooks/.

    python scripts/make_notebooks.py notebooks

Overwrites the notebooks and clears their outputs. Edit this file, not the .ipynb files.
"""
import base64
import hashlib
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat as nbf

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)


def setup(nb_id: str) -> str:
    return f'''# ── Settings ────────────────────────────────────────────────────────────
SHOW_LIVE_LOGS = False  # True = print every node's live log line, like the terminal does

# Setup: run from the repo root, and give this notebook its own database files in
# .notebook_state/ so it never touches the app's checkpoints.sqlite / account_memory.sqlite.
import logging
import os
import sys
import warnings
from pathlib import Path

if "google.colab" in sys.modules:
    # Google Colab: the notebook needs the whole repo (it imports core/, agents/, tools/),
    # so clone it and install the pinned packages on first run; later runs pull updates.
    import subprocess

    REPO = Path("/content/fintech-agent")
    if not REPO.exists():
        print("Colab: cloning the repo and installing packages (about a minute)...")
        subprocess.run(["git", "clone", "-q", "-b", "develop-gemini",
                        "https://github.com/iam-suraj-kumar/fintech-agent.git", str(REPO)], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(REPO / "requirements.txt")], check=True)
        print("Done. If a later cell fails to import, use Runtime > Restart session and run this cell again.")
    else:
        # Already cloned in this Colab session: pick up any fixes pushed since.
        # (Code already imported stays old until Runtime > Restart session.)
        pulled = subprocess.run(["git", "-C", str(REPO), "pull", "-q", "--ff-only"], capture_output=True, text=True)
        if pulled.returncode != 0:
            print("Colab: could not update the repo:", pulled.stderr.strip())
    os.chdir(REPO)
    try:
        from google.colab import userdata  # add GEMINI_API_KEY under the key icon (Secrets) in the sidebar

        os.environ.setdefault("GEMINI_API_KEY", userdata.get("GEMINI_API_KEY"))
    except Exception:
        print("No GEMINI_API_KEY secret found: notebooks 00 and 01 still work; 02-04 need it.")

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
STATE_DIR = ROOT / ".notebook_state"
STATE_DIR.mkdir(exist_ok=True)
os.environ["CHECKPOINT_DB_PATH"] = str(STATE_DIR / "{nb_id}_checkpoints.sqlite")
os.environ["MEMORY_DB_PATH"] = str(STATE_DIR / "{nb_id}_memory.sqlite")
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")  # quiet the MCP server subprocess
warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")  # never overrides the two database paths set above

import pandas as pd

pd.set_option("display.max_colwidth", None)  # show agent findings in full, not cut off with "..."


def trace_table(audit_log: list[dict]) -> pd.DataFrame:
    """One readable line per audit entry (entries have different fields, so a raw table is mostly blanks)."""
    def detail(e: dict) -> str:
        if e["kind"] == "tool_call":
            return f"calls {{e['tool']}}({{e['args']}})"
        if e["kind"] == "tool_result":
            return f"{{e['tool']}} returned {{e['result']}}"
        return str(e.get("text", ""))
    return pd.DataFrame([{{"node": e.get("node", ""), "kind": e["kind"], "detail": detail(e)}} for e in audit_log])

from html import escape

from langchain_core.runnables.graph import NodeStyles

# Explicit colours so the boxes read on both light and dark themes
# (LangGraph's default fills are pale but leave the text colour to the theme).
GRAPH_STYLES = NodeStyles(
    default="fill:#DCE6FA,stroke:#2459C2,stroke-width:1px,color:#15202E,line-height:1.2",
    first="fill:#2459C2,stroke:#2459C2,color:#FFFFFF",
    last="fill:#2F7A4A,stroke:#2F7A4A,color:#FFFFFF",
)


class _MermaidGraph:
    """Displays Mermaid code as a diagram. JupyterLab and VS Code draw Mermaid themselves;
    Colab doesn't, so there the browser draws it with Mermaid's JavaScript."""

    def __init__(self, source: str):
        self.source = source

    def _repr_mimebundle_(self, include=None, exclude=None):
        html = (
            '<div style="background:#fff;padding:10px;border-radius:6px;display:inline-block">'
            '<pre class="mermaid">' + escape(self.source) + "</pre></div>"
            '<script type="module">'
            'import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";'
            'mermaid.initialize({{startOnLoad: false, theme: "default"}});'
            'await mermaid.run({{querySelector: "pre.mermaid:not([data-processed])"}});'
            "</script>"
        )
        if "google.colab" in sys.modules:
            return {{"text/html": html}}
        return {{"text/markdown": "```mermaid\\n" + self.source + "\\n```"}}


def show_graph(app):
    """Draw a compiled LangGraph graph."""
    return _MermaidGraph(app.get_graph().draw_mermaid(node_colors=GRAPH_STYLES))

import core.audit  # noqa: F401  (creates the "fraud_guard" live logger)
from core.llm import llm_model, llm_provider

logging.getLogger("fraud_guard").setLevel(logging.INFO if SHOW_LIVE_LOGS else logging.WARNING)
pd.set_option("display.max_colwidth", 160)
key = {{"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}}.get(llm_provider(), "?")
print(f"LLM: {{llm_provider()}} / {{llm_model()}}   ({{key}} set: {{'yes' if os.environ.get(key) else 'NO'}})")'''


SETUP_NOTE = '''
### Setup
The next cell connects the notebook to the project. It gives this notebook **its own** database files in `.notebook_state/`, so nothing here touches the Streamlit app's data. It prints which LLM this run uses and whether its key is set (never the key itself). Set `SHOW_LIVE_LOGS = True` to see each node's live log line.
'''


_MERMAID_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.S)
DIAGRAMS = Path(__file__).resolve().parent.parent / "notebooks" / "diagrams"
_used_diagrams: set[str] = set()


def _diagram_png(source: str) -> tuple[str, bytes]:
    """PNG for a Mermaid diagram, cached in notebooks/diagrams/ by content hash.

    Only a new or changed diagram needs rendering, which takes mermaid-cli: set MMDC to its
    command, e.g. MMDC="mmdc -p puppeteer.json" (see docs/slides_src or mermaid-cli's README).
    """
    name = hashlib.sha1(source.encode()).hexdigest()[:12] + ".png"
    path = DIAGRAMS / name
    _used_diagrams.add(name)
    if not path.exists():
        if not os.environ.get("MMDC"):
            sys.exit(f"Diagram {name} is new or changed; set MMDC to a mermaid-cli command to render it.")
        DIAGRAMS.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "diagram.mmd"
            src.write_text(source)
            subprocess.run([*shlex.split(os.environ["MMDC"]), "-i", str(src), "-o", str(path),
                            "-b", "white", "-s", "2", "-q"], check=True)
    return name, path.read_bytes()


def md(text):
    # Diagrams are embedded as PNG attachments, not Mermaid: Colab and GitHub don't render
    # Mermaid in Markdown, and an attachment shows everywhere with no internet connection.
    attachments = {}

    def to_image(match: re.Match) -> str:
        name, png = _diagram_png(match.group(1))
        attachments[name] = {"image/png": base64.b64encode(png).decode()}
        return f"![diagram](attachment:{name})"

    source = _MERMAID_BLOCK.sub(to_image, text.strip())
    cell = nbf.v4.new_markdown_cell(source)
    if attachments:
        cell["attachments"] = attachments
    return cell


def code(text):
    return nbf.v4.new_code_cell(text.strip())


def save(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    nbf.write(nb, OUT / name)
    print("wrote", OUT / name)


GRAPH_DIAGRAM = '''```mermaid
flowchart LR
  I["ingest"] --> T{"triage<br/>rules, no LLM"}
  T -->|"score < 0.30"| AA["auto_approve"]
  T -->|"score ≥ 0.65"| AD["auto_decline"]
  T -->|"in between"| TA["transaction_analyst"]
  T -->|"in between"| IV["identity_verifier"]
  T -->|"in between"| PD["pattern_detector"]
  TA --> AG["aggregator"]
  IV --> AG
  PD --> AG
  AG -->|"composite ≥ 0.5"| HR["human_review<br/>pauses here"]
  AG -->|"below 0.5"| R["resolution"]
  HR --> R
  AA --> R
  AD --> R
  R --> E(["END"])
```'''

# =========================================================================== 00 start here
save("00_start_here.ipynb", [
    md('''
# 00 · Start here: the problem, the idea, and LangGraph from scratch

**You'll learn:** why fraud detection needs more than rules or "just ask an LLM", the tiered design this project uses, and the LangGraph building blocks it is made of: state, nodes, edges, routing, parallel branches, pausing for a human, and memory. Each block gets a tiny toy example.

**Time:** about 15 minutes · **Cost:** free · **Needs:** nothing beyond the installed project. No API key, no LLM calls.

| Part | What it covers |
|---|---|
| 1 | The problem |
| 2 | The idea: tiered escalation |
| 3 | Setup |
| 4 | LangGraph building blocks, hands-on: 4.1 state, nodes, edges · 4.2 routing · 4.3 parallel branches · 4.4 pause for a human · 4.5 memory across runs |
| 5 | Where to go next |
'''),
    md('''
---
## Part 1 · The problem

A payments company sees millions of transactions. A few are fraud. Two obvious approaches both fail:

| Approach | Strength | What goes wrong |
|---|---|---|
| **Rules only** ("block anything over $5,000 abroad") | instant, free, predictable | rigid: misses fraud that doesn't break a rule, and blocks honest customers who do |
| **An LLM investigates every transaction** | reasons about context ("is a new device suspicious *for this account*?") | slow and expensive: 3–4 LLM calls on each of millions of transactions, when 95%+ are obvious |

And for the truly hard cases there is a third requirement: **someone accountable decides.** Nobody wants an LLM alone freezing a customer's $18,000 wire transfer.
'''),
    md('''
---
## Part 2 · The idea: tiered escalation

Spend effort only where it is needed:

1. **Triage** with cheap rules: obvious cases are approved or declined instantly, with no LLM.
2. **Investigate** only the ambiguous middle: three AI specialists look at it in parallel, each from a different angle.
3. **Aggregate** their findings into one risk score and explanation.
4. **Ask a human** when risk stays high. The pipeline pauses, saves its state to disk, and waits.
5. **Resolve** and remember the decision for next time.

''' + GRAPH_DIAGRAM + '''

Every box is a **node** in a LangGraph graph. Part 4 builds each mechanism on toy examples first.
'''),
    md('''
---
## Part 3 · Setup
''' + SETUP_NOTE),
    code(setup("00")),
    md('''
---
## Part 4 · LangGraph building blocks, hands-on

### 4.1 State, nodes and edges

A LangGraph app is a **graph**:
- **State**: one shared dictionary (here a `TypedDict`) that flows through the graph.
- **Node**: a plain Python function. It receives the state and returns **only the keys it changes**.
- **Edge**: "after this node, run that one". `START` and `END` mark the entry and exit.

`compile()` turns the description into something you can `invoke()`.
'''),
    code('''
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

show = show_graph  # defined in the setup cell: draws a compiled graph as a picture


class ToyState(TypedDict):
    amount: float
    note: str


def check_amount(state: ToyState) -> dict:
    return {"note": "small purchase" if state["amount"] < 100 else "large purchase"}


builder = StateGraph(ToyState)
builder.add_node("check_amount", check_amount)
builder.add_edge(START, "check_amount")
builder.add_edge("check_amount", END)
toy = builder.compile()

print(toy.invoke({"amount": 6.50, "note": ""}))
show(toy)
'''),
    md('''
**What to notice:** the node returned only `note`, and LangGraph merged it into the state.

### 4.2 Routing with a conditional edge

A **conditional edge** calls a small *router* function that looks at the state and returns the name of the next node. In Fraud Guard, `route_after_triage()` picks approve, decline or investigate, and `route_after_aggregator()` picks human review or resolution.
'''),
    code('''
class TxnState(TypedDict):
    amount: float
    decision: str


def score(state: TxnState) -> dict:
    return {}


def route(state: TxnState) -> str:
    return "approve" if state["amount"] < 100 else "review"


builder = StateGraph(TxnState)
builder.add_node("score", score)
builder.add_node("approve", lambda s: {"decision": "approved"})
builder.add_node("review", lambda s: {"decision": "sent for review"})
builder.add_edge(START, "score")
builder.add_conditional_edges("score", route, {"approve": "approve", "review": "review"})
builder.add_edge("approve", END)
builder.add_edge("review", END)
router_app = builder.compile()

for amount in (6.50, 18000):
    print(amount, "->", router_app.invoke({"amount": amount, "decision": ""})["decision"])
show(router_app)
'''),
    md('''
### 4.3 Parallel branches and reducers

When one node has edges to **several** nodes, they run **in parallel** (fan-out); edges from all of them into one node wait for every branch (fan-in). That is how the three specialists run at the same time.

Parallel nodes writing to the **same** key need a rule for combining their writes: a **reducer**. `Annotated[list, operator.add]` means "append". Fraud Guard's `audit_log` works exactly like this. Without a reducer, LangGraph refuses the conflicting writes, as the second cell shows.
'''),
    code('''
import operator
from typing import Annotated


class InvestigationState(TypedDict):
    findings: Annotated[list[str], operator.add]  # reducer: parallel writes are appended


def build_investigation(state_type):
    builder = StateGraph(state_type)
    builder.add_node("start", lambda s: {})
    builder.add_node("analyst", lambda s: {"findings": ["analyst: amount is 4x the usual"]})
    builder.add_node("identity", lambda s: {"findings": ["identity: new device"]})
    builder.add_node("patterns", lambda s: {"findings": ["patterns: resembles a known scam"]})
    builder.add_node("combine", lambda s: {"findings": [f"combined {len(s['findings'])} findings"]})
    builder.add_edge(START, "start")
    for name in ("analyst", "identity", "patterns"):
        builder.add_edge("start", name)   # fan-out: all three run in parallel
        builder.add_edge(name, "combine")  # fan-in: combine waits for all three
    builder.add_edge("combine", END)
    return builder.compile()


parallel_app = build_investigation(InvestigationState)
for line in parallel_app.invoke({"findings": []})["findings"]:
    print(line)
show(parallel_app)
'''),
    code('''
class NoReducerState(TypedDict):
    findings: list[str]  # no reducer


try:
    build_investigation(NoReducerState).invoke({"findings": []})
except Exception as exc:
    print(type(exc).__name__, "->", str(exc)[:160])
'''),
    md('''
### 4.4 Pausing for a human: interrupts and checkpoints

Two features work together:
- A **checkpointer** saves the state after every step, keyed by a `thread_id` (one per run).
- `interrupt_before=["human_review"]` stops the graph **before** that node runs.

The run then waits. Later (seconds or days, even after a restart when the checkpointer writes to disk), you add the human's decision with `update_state()` and continue with `invoke(None, config)`. Fraud Guard uses a SQLite checkpointer; this toy uses an in-memory one.
'''),
    code('''
from langgraph.checkpoint.memory import InMemorySaver


class ReviewState(TypedDict):
    amount: float
    human_decision: str
    final: str


builder = StateGraph(ReviewState)
builder.add_node("triage", lambda s: {})
builder.add_node("human_review", lambda s: {})
builder.add_node("resolve", lambda s: {"final": f"{s['human_decision']}d by a human"})
builder.add_edge(START, "triage")
builder.add_edge("triage", "human_review")
builder.add_edge("human_review", "resolve")
builder.add_edge("resolve", END)
review_app = builder.compile(checkpointer=InMemorySaver(), interrupt_before=["human_review"])

config = {"configurable": {"thread_id": "toy-wire-1"}}
review_app.invoke({"amount": 18000, "human_decision": "", "final": ""}, config)
print("paused before:", review_app.get_state(config).next)

review_app.update_state(config, {"human_decision": "approve"})  # the reviewer clicks Approve
print("after resume:", review_app.invoke(None, config)["final"])
show(review_app)
'''),
    md('''
### 4.5 Memory across runs: the store

The checkpointer remembers **one run**. A **store** remembers things **across runs**, organised by namespace, e.g. `("account_memory", "acct_2002")`. Nodes read it with `get_store()`. Fraud Guard's `resolution` node writes each decision; next time, `triage` reads the account's history and raises the risk score if it was escalated or declined before.
'''),
    code('''
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
store.put(("account_memory", "acct_2002"), "txn_003", {"final_decision": "escalated"})
store.put(("account_memory", "acct_2002"), "txn_004", {"final_decision": "approved"})
[item.value for item in store.search(("account_memory", "acct_2002"))]
'''),
    md('''
---
## Part 5 · Where to go next

| Notebook | What you'll do | API key? |
|---|---|---|
| **01_triage_rules** | The rule engine: signals, scores, thresholds, routing, the memory penalty, and how much traffic reaches the LLM | no |
| **02_specialist_agents** | Tools, the fraud-case search, the live MCP geolocation server, ReAct agents, the three specialists and the aggregator | yes |
| **03_full_graph** | The whole graph on real scenarios: auto paths, the pause for review, the human decision, the audit trail | yes |
| **04_persistence_and_memory** | Surviving a restart mid-review, checkpoint history, long-term account memory, Studio, CLI and app | yes |

Each notebook runs on its own.
'''),
])

# =========================================================================== 01 triage
save("01_triage_rules.ipynb", [
    md('''
# 01 · Triage: the rule engine that decides who gets an LLM

**You'll learn:** what a transaction looks like, which signals triage scores, how the thresholds route each transaction, how account memory raises the score, and how much traffic actually reaches the expensive AI agents.

**Time:** about 10 minutes · **Cost:** free · **Needs:** no API key; triage uses no LLM.

```mermaid
flowchart LR
  T["transaction"] --> S["5 signals + memory penalty<br/>nodes/triage.py"]
  S --> SC["score 0.0 – 1.0"]
  SC -->|"< 0.30"| A["auto_approve"]
  SC -->|"0.30 – 0.65"| I["investigate<br/>3 AI specialists"]
  SC -->|"≥ 0.65"| D["auto_decline"]
```

| Part | What it covers | Code |
|---|---|---|
| 1 | Setup | |
| 2 | The transactions | `data/synthetic_transactions.py` |
| 3 | The data triage looks up | `tools/mock_apis.py` |
| 4 | The scoring rules, signal by signal | `nodes/triage.py` |
| 5 | Routing | `nodes/triage.py: route_after_triage()` |
| 6 | Account memory raises the score | `nodes/triage.py: _account_memory_penalty()` |
| 7 | How much traffic reaches the LLM? | |
| 8 | Recap and things to try | |
'''),
    md('''
---
## Part 1 · Setup
''' + SETUP_NOTE),
    code(setup("01")),
    md('''
---
## Part 2 · The transactions

Four hand-made scenarios drive the demo. Each is a plain dictionary: who paid (`account_id`), how much, to which merchant, from which device and IP, and for wires, to which beneficiary. `ip` is a key into the mock geolocation table; `real_ip` is a genuine public IP for the live MCP lookup in notebook 02.
'''),
    code('''
from data.synthetic_transactions import SCENARIOS, get_scenario

pd.DataFrame(SCENARIOS).T[["transaction_id", "account_id", "amount", "merchant_id", "device_id", "ip", "type", "beneficiary_name"]].fillna("")  # only wires have a beneficiary
'''),
    md('''
Any other ID also works: `get_scenario()` hashes it into a seeded random generator, so the same ID always produces the same plausible transaction (about 1 in 7 lean risky). That is how an audience member can shout out any ID during a demo.
'''),
    code('''
own = get_scenario("audience-question-42")
assert own == get_scenario("audience-question-42")  # same ID -> same transaction, every time
own
'''),
    md('''
---
## Part 3 · The data triage looks up

Triage enriches each transaction with four lookups. In this demo they are mock tables (a real system would call internal services):
'''),
    code('''
from tools.mock_apis import ACCOUNT_HISTORY, DEVICE_FINGERPRINTS, GEOLOCATIONS, MERCHANT_RISK

accounts = {t["account_id"] for t in SCENARIOS.values()}
display(pd.DataFrame({a: ACCOUNT_HISTORY[a] for a in sorted(accounts)}).T.rename_axis("account"))
display(pd.DataFrame({m: MERCHANT_RISK[m] for m in sorted({t["merchant_id"] for t in SCENARIOS.values()})}).T.rename_axis("merchant"))
display(pd.DataFrame(DEVICE_FINGERPRINTS).T.rename_axis("device"))
pd.DataFrame(GEOLOCATIONS).T.rename_axis("ip key")
'''),
    md('''
---
## Part 4 · The scoring rules, signal by signal

`_compute_triage_score()` adds up points for each warning sign and caps the total at 1.0. This is the real code:
'''),
    code('''
import inspect

from nodes.triage import AUTO_DECLINE_THRESHOLD, INVESTIGATE_THRESHOLD, _compute_triage_score

print(inspect.getsource(_compute_triage_score))
'''),
    md('''
The same rules as a table, one column per signal. The helper below restates the code above so each signal's points are visible; the `assert` checks that its total equals the real function's score, so the table can't drift from the code.
'''),
    code('''
from tools.mock_apis import get_account_history, get_device_fingerprint, get_geolocation, get_merchant_risk_score


def breakdown(t: dict) -> dict:
    high = get_account_history(t["account_id"])["typical_range"][1]
    amount = 0.35 if t["amount"] > high * 3 else 0.15 if t["amount"] > high else 0.0
    device = 0.0 if get_device_fingerprint(t["device_id"])["known"] else 0.15
    merchant = get_merchant_risk_score(t["merchant_id"])["score"] * 0.2
    beneficiary = 0.15 if t.get("beneficiary_is_new") else 0.0
    travel = 0.0
    if t.get("prior_ip") and t["prior_ip"] != t["ip"]:
        if get_geolocation(t["prior_ip"])["country"] != get_geolocation(t["ip"])["country"]:
            travel = 0.55
    total = min(amount + device + merchant + beneficiary + travel, 1.0)
    assert abs(total - _compute_triage_score(t)) < 1e-9  # outside a graph the memory penalty is 0
    return {"unusual amount": amount, "unknown device": device, "merchant risk": round(merchant, 3),
            "new beneficiary": beneficiary, "impossible travel": travel, "SCORE": round(total, 3)}


scores = pd.DataFrame({name: breakdown(t) for name, t in SCENARIOS.items()}).T
scores
'''),
    md('''
**What to notice:** no single signal decides. The $18,000 wire is unusual (3.6× the account's maximum), to a high-risk merchant and a new beneficiary, but from a known device, so it lands in the middle. Impossible travel alone (US to Nigeria in 10 minutes) adds 0.55.

The chart places each scenario between the two thresholds:
'''),
    code('''
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 2.8))
ax.axvspan(0, INVESTIGATE_THRESHOLD, color="#E3F1E6", label="auto_approve")
ax.axvspan(INVESTIGATE_THRESHOLD, AUTO_DECLINE_THRESHOLD, color="#FBE9DC", label="investigate (LLM)")
ax.axvspan(AUTO_DECLINE_THRESHOLD, 1.0, color="#F6D6D6", label="auto_decline")
ax.barh(scores.index, scores["SCORE"], color="#2459C2", height=0.5)
for i, value in enumerate(scores["SCORE"]):
    ax.text(value + 0.01, i, f"{value:.2f}", va="center")
ax.set_xlim(0, 1.0)
ax.set_xlabel("triage score")
ax.legend(loc="lower right", fontsize=8)
plt.show()
'''),
    md('''
---
## Part 5 · Routing

`triage_node()` turns the score into a decision; `route_after_triage()` turns the decision into the next node or nodes. For `investigate` it returns **three** node names, which is LangGraph's fan-out: all three specialists start in parallel.
'''),
    code('''
from core.state import new_state
from nodes.triage import route_after_triage, triage_node

rows = []
for name, t in SCENARIOS.items():
    update = triage_node(new_state(t))
    rows.append({"scenario": name, "score": round(update["triage_score"], 3),
                 "decision": update["triage_decision"], "next nodes": route_after_triage(update)})
pd.DataFrame(rows)
'''),
    md('''
---
## Part 6 · Account memory raises the score

After every decision, the `resolution` node writes it to the long-term store under `("account_memory", account_id)`. Triage reads it back: **+0.15 per past escalation, +0.10 per past decline, at most +0.30.**

`get_store()` only works inside a graph, so this cell wraps the real `triage_node` in a one-node graph with an in-memory store, scores `borderline_restart_demo`, then adds two past escalations for the same account and scores it again.
'''),
    code('''
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore

from core.state import TransactionState


def triage_with(store):
    builder = StateGraph(TransactionState)
    builder.add_node("triage", triage_node)
    builder.add_edge(START, "triage")
    builder.add_edge("triage", END)
    return builder.compile(store=store)


txn = SCENARIOS["borderline_restart_demo"]
store = InMemoryStore()
before = triage_with(store).invoke(new_state(txn))
for i in range(2):
    store.put(("account_memory", txn["account_id"]), f"past-{i}", {"final_decision": "escalated"})
after = triage_with(store).invoke(new_state(txn))

pd.DataFrame([
    {"account history": "clean", "score": round(before["triage_score"], 3), "decision": before["triage_decision"]},
    {"account history": "2 past escalations", "score": round(after["triage_score"], 3), "decision": after["triage_decision"]},
])
'''),
    md('''
**What to notice:** the same transaction moves from *investigate* to *auto_decline* because the account has a track record. This is also why the app wipes memory on start by default (`RESET_MEMORY_ON_START=true`): repeated rehearsals on the same demo account would otherwise auto-decline it.

---
## Part 7 · How much traffic reaches the LLM?

The point of triage is cost. Generating 500 random transactions and triaging them shows the split: only the middle band pays for LLM calls.
'''),
    code('''
sample = [get_scenario(f"random-{i}") for i in range(500)]
decisions = pd.Series([triage_node(new_state(t))["triage_decision"] for t in sample]).value_counts()
display(decisions.to_frame("transactions").assign(share=lambda d: (d.transactions / d.transactions.sum()).map("{:.0%}".format)))

fig, ax = plt.subplots(figsize=(6, 2.4))
colors = {"auto_approve": "#3C8D5A", "investigate": "#C2560F", "auto_decline": "#B23A3A"}
ax.barh(decisions.index, decisions.values, color=[colors[d] for d in decisions.index])
ax.set_xlabel("transactions out of 500")
plt.show()
'''),
    md('''
---
## Part 8 · Recap and things to try

**What happened:** each transaction got points for five warning signs plus its account's history; the total routed it to approve, decline, or the three AI specialists. No LLM was called.

**Try this**
- Make a transaction of your own: copy `SCENARIOS["borderline_wire"]`, change the amount to 3,000, and run `breakdown()` on it.
- Move a threshold: what share goes to `investigate` if `INVESTIGATE_THRESHOLD` were 0.20?
- Add a past *decline* instead of an escalation in Part 6. How much does the score move?

**Next:** `02_specialist_agents.ipynb`: the three AI specialists that investigate the middle band.
'''),
])

# =========================================================================== 02 specialists
save("02_specialist_agents.ipynb", [
    md('''
# 02 · The specialist agents: tools, RAG, MCP and ReAct

**You'll learn:** what an agent's tools are, how the fraud-case search (RAG) and the live MCP geolocation server work, how a ReAct agent decides which tool to call, how the three specialists differ, and how the aggregator turns their findings into one score.

**Time:** about 10 minutes · **Cost:** free tier or about 1¢ · **Needs:** an API key in `.env` (`GEMINI_API_KEY` by default).

```mermaid
flowchart LR
  T["borderline transaction"] --> TA["transaction_analyst<br/>account_history · merchant_risk_score · sanctions_check"]
  T --> IV["identity_verifier<br/>device_fingerprint · geolocation (live MCP)"]
  T --> PD["pattern_detector<br/>account_history · similar_fraud_cases (RAG)"]
  TA --> AG["aggregator<br/>structured output: composite_score + reasoning"]
  IV --> AG
  PD --> AG
```

| Part | What it covers | Code |
|---|---|---|
| 1 | Setup | |
| 2 | Tools: what agents can call | `tools/llm_tools.py`, `tools/mock_apis.py` |
| 3 | RAG: searching past fraud cases | `tools/mock_apis.py: search_similar_fraud_cases()` |
| 4 | MCP: a live geolocation server | `mcp_server/geolocation_server.py`, `tools/mcp_geolocation.py` |
| 5 | ReAct: one agent, step by step | `core/specialist_factory.py` |
| 6 | All three specialists | `agents/` |
| 7 | The aggregator | `nodes/aggregator.py` |
| 8 | Recap and things to try | |
'''),
    md('''
---
## Part 1 · Setup
''' + SETUP_NOTE),
    code(setup("02")),
    md('''
---
## Part 2 · Tools: what agents can call

A **tool** is a Python function the LLM may ask to run. The `@tool` decorator turns its name, docstring and arguments into a description the model reads to decide when to call it. The model never runs code itself: it replies "call `account_history` with `acct_2002`", the framework runs the function, and the result goes back to the model.
'''),
    code('''
from tools.llm_tools import account_history, device_fingerprint, merchant_risk_score, sanctions_check, similar_fraud_cases

pd.DataFrame([
    {"tool": t.name, "arguments": list(t.args), "description the LLM reads": t.description}
    for t in (account_history, merchant_risk_score, sanctions_check, device_fingerprint, similar_fraud_cases)
])
'''),
    md('''
Calling tools directly, the way an agent would, for the two wire transfers. Note the sanctions check: `borderline_restart_demo` pays "Silk Road Holdings Ltd", which is on the mock watchlist.
'''),
    code('''
from data.synthetic_transactions import SCENARIOS

for name in ("borderline_wire", "borderline_restart_demo"):
    t = SCENARIOS[name]
    print(f"===== {name}: ${t['amount']:,.0f} to {t['beneficiary_name']}")
    print("account_history     ", account_history.invoke({"account_id": t["account_id"]}))
    print("merchant_risk_score ", merchant_risk_score.invoke({"merchant_id": t["merchant_id"]}))
    print("device_fingerprint  ", device_fingerprint.invoke({"device_id": t["device_id"]}))
    print("sanctions_check     ", sanctions_check.invoke({"beneficiary_name": t["beneficiary_name"]}), "\\n")
'''),
    md('''
---
## Part 3 · RAG: searching past fraud cases

`similar_fraud_cases` is retrieval-augmented generation in miniature: a handful of past confirmed fraud cases are embedded into an in-memory **Chroma** vector store (using the embedding model of your provider), and the tool returns the 2 most similar to a description. The `pattern_detector` uses it to ask "have we seen this before?".
'''),
    code('''
from tools.mock_apis import FRAUD_CASE_TEXTS

print(f"{len(FRAUD_CASE_TEXTS)} past cases in the store, e.g.:\\n- {FRAUD_CASE_TEXTS[0]}\\n")
query = "Large international wire transfer to a brand-new beneficiary from a business account"
for case in similar_fraud_cases.invoke({"description": query}):
    print("match:", case)
'''),
    md('''
---
## Part 4 · MCP: a live geolocation server

Everything else in the demo is mock data, but the `identity_verifier`'s geolocation is **real**. It comes from a separate **MCP server** (Model Context Protocol, a standard way to expose tools to AI apps):

```mermaid
flowchart LR
  A["identity_verifier agent"] --> C["MCP client<br/>langchain-mcp-adapters"]
  C -->|"stdio: starts a subprocess"| S["mcp_server/geolocation_server.py<br/>FastMCP tool: geolocation(ip)"]
  S -->|"HTTP"| API["ip-api.com"]
```

The first call starts the server process; `get_geolocation_tool()` wraps its async tool for the synchronous agents. Compare the live answer with the mock table triage used:
'''),
    code('''
from tools.mcp_geolocation import get_geolocation_tool
from tools.mock_apis import get_geolocation

geo = get_geolocation_tool()
for name in ("impossible_travel", "borderline_wire"):
    t = SCENARIOS[name]
    print(f"{name}: mock {t['ip']} -> {get_geolocation(t['ip'])} | live {t['real_ip']} -> {geo.invoke({'ip': t['real_ip']})}")
'''),
    md('''
**What to notice:** the impossible-travel IP genuinely resolves to Nigeria, which is what makes the agent's write-up convincing rather than scripted.

---
## Part 5 · ReAct: one agent, step by step

Each specialist is a **ReAct agent** (reason + act), built with LangGraph's `create_react_agent`:

```mermaid
flowchart LR
  P["system prompt + transaction"] --> L{"LLM"}
  L -->|"tool call"| T["run the tool"]
  T -->|"result"| L
  L -->|"no more tool calls"| F["final finding: 2–3 sentences"]
```

The LLM keeps choosing tools until it has enough, then writes its finding. `make_specialist_node()` wraps an agent into a graph node and records every tool call and result in the audit log. Running the transaction analyst on the wire to "Silk Road Holdings Ltd":
'''),
    code('''
from agents.transaction_analyst import SYSTEM_PROMPT, transaction_analyst_node
from core.state import new_state

print("SYSTEM PROMPT:", SYSTEM_PROMPT, "\\n")
update = transaction_analyst_node(new_state(SCENARIOS["borderline_restart_demo"]))

display(trace_table(update["audit_log"]))
print("FINDING:", update["analyst_findings"])
'''),
    md('''
**What to notice:** the model decided on its own to call `sanctions_check` because the prompt says to when a beneficiary is present, and it leads its finding with the watchlist hit. Adding that skill took one more tool in a list; the graph did not change.

---
## Part 6 · All three specialists

Same factory, different prompts and tools. Each investigates one independent angle, which is why they can run in parallel in the graph. Here they run one after another on the $18,000 wire:
'''),
    code('''
from agents.identity_verifier import identity_verifier_node
from agents.pattern_detector import pattern_detector_node

state = new_state(SCENARIOS["borderline_wire"])
findings = {}
for node, key in ((transaction_analyst_node, "analyst_findings"),
                  (identity_verifier_node, "identity_findings"),
                  (pattern_detector_node, "pattern_findings")):
    result = node(state)
    findings[key] = result[key]
    tools_used = [e["tool"] for e in result["audit_log"] if e["kind"] == "tool_call"]
    print(f"===== {key} (tools: {tools_used})\\n{result[key]}\\n")
'''),
    md('''
---
## Part 7 · The aggregator

Three free-text opinions must become **one** number a router can compare. The aggregator asks the LLM for **structured output**: a Pydantic model with exactly two fields, so the reply is always parseable.
'''),
    code('''
from nodes.aggregator import AGGREGATOR_THRESHOLD, AggregatorOutput, aggregator_node, route_after_aggregator
from nodes.triage import triage_node

print({name: field.description for name, field in AggregatorOutput.model_fields.items()}, "\\n")
state = {**state, **triage_node(state), **findings}
result = aggregator_node(state)
print(f"composite_score = {result['composite_score']:.2f}  (human review at ≥ {AGGREGATOR_THRESHOLD})")
print("reasoning:", result["aggregate_reasoning"])
print("next node:", route_after_aggregator({**state, **result}))
'''),
    md('''
---
## Part 8 · Recap and things to try

**What happened:** tools gave the agents facts (mock services, a vector search over past fraud, and a live MCP server); each ReAct agent chose its own tool calls and wrote a short finding; the aggregator merged them into a structured score that decides whether a human must look.

**Try this**
- Run `identity_verifier_node` on `SCENARIOS["impossible_travel"]` and read how it uses the live Nigeria lookup.
- Search the fraud cases for "small test charges followed by a large purchase".
- Add a tool: write a `@tool` function and add it to one specialist's list in `agents/`. Nothing else changes.

**Next:** `03_full_graph.ipynb` runs all of this inside the real graph, including the pause for human review.
'''),
])

# =========================================================================== 03 full graph
save("03_full_graph.ipynb", [
    md('''
# 03 · The full graph: from transaction to decision

**You'll learn:** how `graph.py` wires the nodes together, what happens on each path (approve, decline, investigate), how the run pauses for a human, how the decision resumes it, and how to read the audit trail.

**Time:** about 10 minutes · **Cost:** free tier or about 1¢ · **Needs:** an API key in `.env`.

''' + GRAPH_DIAGRAM + '''

| Part | What it covers | Code |
|---|---|---|
| 1 | Setup | |
| 2 | The wiring | `graph.py: build_graph()` |
| 3 | The fast paths: no LLM | |
| 4 | The investigate path, paused for review | |
| 5 | The human decision | `ui/logic.py: resume_transaction()` |
| 6 | Any transaction ID | |
| 7 | Recap and things to try | |
'''),
    md('''
---
## Part 1 · Setup
''' + SETUP_NOTE + '''
Importing `graph` builds the real compiled graph with a SQLite checkpointer and store, pointed at this notebook's own files.
'''),
    code(setup("03") + '''

import uuid

from core.state import new_state
from data.synthetic_transactions import SCENARIOS, get_scenario
from graph import build_graph, graph


def new_thread(name: str) -> dict:
    # One thread_id per run, like the app: the checkpointer keys saved state by it.
    return {"configurable": {"thread_id": f"{name}-{uuid.uuid4().hex[:6]}"}}


def audit_table(values: dict) -> pd.DataFrame:
    return trace_table(values["audit_log"])'''),
    md('''
---
## Part 2 · The wiring

`build_graph()` is the whole pipeline in about 30 lines: add the 10 nodes, connect them with edges, add the two routers as conditional edges, and compile with a checkpointer, a store and `interrupt_before=["human_review"]`. This is the real code:
'''),
    code('''
import inspect

print(inspect.getsource(build_graph))
'''),
    md('''
LangGraph can draw the compiled graph itself. Dotted arrows are conditional edges; `human_review` is marked as an interrupt.
'''),
    code('''
show_graph(graph)
'''),
    md('''
---
## Part 3 · The fast paths: no LLM

Most traffic ends here. A $6.50 coffee is approved and a US-to-Nigeria purchase 10 minutes after a US one is declined, both by triage alone, in milliseconds.
'''),
    code('''
import time

for name in ("clean_coffee", "impossible_travel"):
    start = time.time()
    out = graph.invoke(new_state(SCENARIOS[name]), new_thread(name))
    print(f"{name}: triage {out['triage_score']:.2f} -> {out['triage_decision']} -> {out['final_decision']} ({(time.time() - start) * 1000:.0f} ms)")
    display(audit_table(out))
'''),
    md('''
---
## Part 4 · The investigate path, paused for review

The $18,000 wire scores in the middle band, so triage fans out to the three specialists **in parallel**, the aggregator scores their findings, and if the composite score is 0.5 or more the graph **stops before `human_review`**. `invoke()` returns, and `get_state()` shows where it is waiting.
'''),
    code('''
wire_config = new_thread("borderline_wire")
start = time.time()
graph.invoke(new_state(SCENARIOS["borderline_wire"]), wire_config)
snapshot = graph.get_state(wire_config)

print(f"took {time.time() - start:.1f}s · waiting before: {snapshot.next}")
print(f"triage {snapshot.values['triage_score']:.2f} · composite {snapshot.values['composite_score']:.2f}")
print("aggregator reasoning:", snapshot.values["aggregate_reasoning"])
'''),
    md('''
The audit trail shows every step so far, including each specialist's tool calls. The three specialists' entries interleave because they ran at the same time:
'''),
    code('''
audit_table(snapshot.values)
'''),
    md('''
---
## Part 5 · The human decision

This is what the Streamlit review queue and `cli.py review` do (`ui/logic.py: resume_transaction()`): write the reviewer's choice into the saved state, then continue the same thread. The choices are `approve`, `decline` or `escalate`.
'''),
    code('''
graph.update_state(wire_config, {"human_decision": "approve"})
final = graph.invoke(None, wire_config)

print("final decision:", final["final_decision"])
audit_table(final).tail(3)
'''),
    md('''
---
## Part 6 · Any transaction ID

Type any ID; it becomes a reproducible synthetic transaction (notebook 01, Part 2). If it pauses for review, this cell declines it.
'''),
    code('''
MY_ID = "conference-demo-7"

config = new_thread(MY_ID)
out = graph.invoke(new_state(get_scenario(MY_ID)), config)
if graph.get_state(config).next:
    graph.update_state(config, {"human_decision": "decline"})
    out = graph.invoke(None, config)
print(f"{MY_ID}: ${out['transaction']['amount']:,.2f} · triage {out['triage_score']:.2f} ({out['triage_decision']}) · final: {out['final_decision']}")
'''),
    md('''
---
## Part 7 · Recap and things to try

**What happened:** one graph handled every path. Cheap rules settled the obvious cases; the ambiguous wire fanned out to three agents in parallel, was scored, and **paused**; a human's decision resumed the same thread to a final, audited outcome.

**Try this**
- Resume a paused run with `"escalate"` instead and check `final_decision`.
- Run `borderline_restart_demo` and read the analyst's sanctions finding in the audit table.
- Try a few IDs in Part 6 until one pauses for review.

**Next:** `04_persistence_and_memory.ipynb`: kill the process mid-review and pick up where it left off.
'''),
])

# =========================================================================== 04 persistence
save("04_persistence_and_memory.ipynb", [
    md('''
# 04 · Persistence and memory: surviving restarts, remembering accounts

**You'll learn:** how the SQLite checkpointer lets a paused review survive a full restart, how to list pending reviews and step through a run's history, how long-term account memory changes the next decision, and where to watch all of this in Studio, the app and the CLI.

**Time:** about 10 minutes · **Cost:** free tier or about 1¢ · **Needs:** an API key in `.env`.

```mermaid
flowchart LR
  subgraph RUN["One run (thread_id)"]
    direction LR
    A["triage → specialists → aggregator"] --> P["paused before human_review"]
    P -->|"update_state + invoke(None)"| R["resolution"]
  end
  P -.->|"every step saved"| CP[("checkpoints.sqlite<br/>SqliteSaver")]
  R -.->|"decision saved"| ST[("account_memory.sqlite<br/>SqliteStore")]
  ST -.->|"read by triage next time"| A
```

| Part | What it covers | Code |
|---|---|---|
| 1 | Setup | |
| 2 | Pause a review, then "restart" | `graph.py`, `langgraph.checkpoint.sqlite` |
| 3 | Pending reviews and run history | `ui/logic.py` |
| 4 | Long-term memory changes the next decision | `nodes/resolution.py`, `nodes/triage.py` |
| 5 | Studio, the app and the CLI | |
| 6 | Recap and things to try | |
'''),
    md('''
---
## Part 1 · Setup
''' + SETUP_NOTE),
    code(setup("04") + '''

import sqlite3
import uuid

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

from core.state import new_state
from data.synthetic_transactions import SCENARIOS
from graph import DEFAULT_NODES, build_graph, graph

CHECKPOINTS = os.environ["CHECKPOINT_DB_PATH"]
MEMORY = os.environ["MEMORY_DB_PATH"]
print("checkpoints:", CHECKPOINTS, "\\nmemory:     ", MEMORY)'''),
    md('''
---
## Part 2 · Pause a review, then "restart"

Start the $9,500 wire to "Silk Road Holdings Ltd". It pauses before `human_review`, and every step is already in `checkpoints.sqlite`.
'''),
    code('''
config = {"configurable": {"thread_id": f"restart-demo-{uuid.uuid4().hex[:6]}"}}
graph.invoke(new_state(SCENARIOS["borderline_restart_demo"]), config)
print("waiting before:", graph.get_state(config).next, "· thread:", config["configurable"]["thread_id"])
'''),
    md('''
Now simulate killing the process: throw away the graph object and build a **brand-new** one from nothing but the same two files on disk. Nothing in memory is reused.
'''),
    code('''
del graph  # the old graph object is gone

fresh_graph = build_graph(
    DEFAULT_NODES,
    checkpointer=SqliteSaver(sqlite3.connect(CHECKPOINTS, check_same_thread=False)),
    store=SqliteStore(sqlite3.connect(MEMORY, check_same_thread=False, isolation_level=None)),
)
restored = fresh_graph.get_state(config)
print("after restart, still waiting before:", restored.next)
print(f"composite score {restored.values['composite_score']:.2f} · analyst: {restored.values['analyst_findings'][:160]}…")
'''),
    md('''
**What to notice:** the pending case, with all three findings, came back from disk. A server deploy or crash in the middle of a review loses nothing.

---
## Part 3 · Pending reviews and run history

The app's review queue is just "every thread whose next step is `human_review`" (`ui/logic.py: get_pending_reviews()`):
'''),
    code('''
from ui.logic import get_pending_reviews

pd.DataFrame([
    {"thread": p["thread_id"], "amount": p["transaction"]["amount"], "composite": round(p["composite_score"], 2)}
    for p in get_pending_reviews(fresh_graph)
])
'''),
    md('''
The checkpointer keeps **every** step, not just the last, so you can see how the state evolved (and, in Studio, rewind to any step):
'''),
    code('''
history = list(fresh_graph.get_state_history(config))
pd.DataFrame([
    {"step": s.metadata.get("step"), "next node": s.next, "audit entries so far": len(s.values.get("audit_log", []))}
    for s in reversed(history)
])
'''),
    md('''
The reviewer escalates it. `resolution` records the decision in long-term memory:
'''),
    code('''
fresh_graph.update_state(config, {"human_decision": "escalate"})
print("final decision:", fresh_graph.invoke(None, config)["final_decision"])
'''),
    md('''
---
## Part 4 · Long-term memory changes the next decision

The checkpointer remembered **one run**. The store remembers **the account** across runs. `borderline_wire` uses the same account, `acct_2002`, which now has one escalation on record:
'''),
    code('''
account = SCENARIOS["borderline_wire"]["account_id"]
store = SqliteStore(sqlite3.connect(MEMORY, check_same_thread=False, isolation_level=None))
memory = [item.value for item in store.search(("account_memory", account))]
print(account, "memory:", memory)
if not memory:
    print("(empty: run the escalate cell above first, or the wire is investigated as if new)")

wire = fresh_graph.invoke(new_state(SCENARIOS["borderline_wire"]), {"configurable": {"thread_id": f"wire-{uuid.uuid4().hex[:6]}"}})
print(f"\\nborderline_wire triage score now {wire['triage_score']:.2f} (0.64 on a clean account) -> {wire['triage_decision']} -> {wire['final_decision']}")
'''),
    md('''
**What to notice:** one escalation added +0.15 and pushed the wire past the 0.65 auto-decline threshold, so this time it was declined instantly with no LLM calls. The app wipes memory on every start by default (`RESET_MEMORY_ON_START=true`) so rehearsals don't snowball like this; set it to `false` to keep memory between runs.

---
## Part 5 · Studio, the app and the CLI

The same graph, three other ways in:

| Tool | Command | What you see |
|---|---|---|
| **LangGraph Studio** | `uv run langgraph dev` | the graph drawn live; run it, watch each node, inspect and rewind state |
| **Streamlit app** | `uv run streamlit run ui/app.py` | submit transactions, the review queue with Approve / Decline / Escalate, history |
| **CLI** | `uv run python cli.py submit borderline_wire` | the same flow in the terminal; `pending`, `review <thread_id> approve`, `history` |
| **LangSmith** (optional) | `LANGSMITH_TRACING=true` in `.env` | every LLM call, tool call and timing, per run |

---
## Part 6 · Recap and things to try

**What happened:** a paused review survived throwing away the whole graph, because every step lives in SQLite; the review queue and step history came straight from the checkpointer; and a decision stored in long-term memory changed how the same account was triaged next time.

**Try this**
- Decide the restored case with `"approve"` instead: does `borderline_wire` still get declined in Part 4?
- Run Part 2, then actually restart the kernel (**Kernel → Restart**), re-run Setup, and look the thread up again with `get_pending_reviews`.
- Open Studio (`uv run langgraph dev`) and run `borderline_wire` there.
'''),
])

# Remove cached diagram images that no notebook uses any more.
for stale in DIAGRAMS.glob("*.png"):
    if stale.name not in _used_diagrams:
        stale.unlink()
