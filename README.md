# Fraud Guard — LangGraph Fintech Demo

A LangGraph demo built for a conference talk: a tiered fraud-detection
pipeline that only pays for expensive multi-agent LLM investigation on
borderline transactions, pauses for human review when risk stays high, and
survives a process restart mid-review thanks to checkpointing. The
`identity_verifier` agent's geolocation lookup is backed by a real local MCP
server hitting a live public IP-geolocation API — everything else stays
synthetic/mock so the rest of the demo runs offline and predictably.

It runs on **Google Gemini** by default (a free key from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)) or on
**OpenAI**, chosen in `.env`. Five step-by-step [notebooks](#notebooks)
teach it from scratch.

## Quickstart

### 1. Setup

```bash
uv sync --dev
cp .env.example .env  # then fill in GEMINI_API_KEY (or see "Choosing a model")
```

`uv sync --dev` creates `.venv` and installs everything from `uv.lock`,
including the dev tools (LangGraph Studio CLI, Jupyter, pytest). Prefix the
run commands below with `uv run` (e.g. `uv run streamlit run ui/app.py ...`),
or run `source .venv/bin/activate` once per shell instead.

#### Without uv (pip or Google Colab)

`requirements.txt` (the app) and `requirements-dev.txt` (adds Jupyter,
matplotlib, pytest and the Studio CLI) are pinned from `uv.lock`, so pip
installs the same versions as `uv sync`. Use Python 3.11–3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # then fill in GEMINI_API_KEY
```

Then run the commands below without the `uv run` prefix (e.g.
`jupyter lab notebooks/`, `python cli.py submit clean_coffee`).

#### Google Colab (no install)

Nothing to set up on your laptop. Each notebook's first cell detects Colab and
does the setup itself: it clones this repo (the notebooks import its code from
`core/`, `agents/` and `tools/`), installs `requirements.txt`, and reads your
key from Colab's Secrets.

1. In Colab, click the **key icon** (Secrets) in the left sidebar, add
   `GEMINI_API_KEY` with your key, and turn on **Notebook access**.
2. Open a notebook below and choose **Runtime → Run all**.

| Notebook | What it covers | Needs a key |
|---|---|---|
| [00_start_here](https://colab.research.google.com/github/iam-suraj-kumar/fintech-agent/blob/develop-gemini/notebooks/00_start_here.ipynb) | the domain and LangGraph basics | no |
| [01_triage_rules](https://colab.research.google.com/github/iam-suraj-kumar/fintech-agent/blob/develop-gemini/notebooks/01_triage_rules.ipynb) | rules triage, no AI | no |
| [02_specialist_agents](https://colab.research.google.com/github/iam-suraj-kumar/fintech-agent/blob/develop-gemini/notebooks/02_specialist_agents.ipynb) | tools, RAG, MCP and the ReAct agents | yes |
| [03_full_graph](https://colab.research.google.com/github/iam-suraj-kumar/fintech-agent/blob/develop-gemini/notebooks/03_full_graph.ipynb) | the whole graph and human review | yes |
| [04_persistence_and_memory](https://colab.research.google.com/github/iam-suraj-kumar/fintech-agent/blob/develop-gemini/notebooks/04_persistence_and_memory.ipynb) | pausing, restarting and memory | yes |

The first run takes about a minute (the clone and install). If Colab asks to
restart the session, or a later cell fails to import, use **Runtime → Restart
session** and run all again: the second time it skips the setup. Each notebook
is its own Colab session, so each one does this once. Files the notebooks save
(paused reviews, account memory) disappear when Colab recycles the session.
Diagrams are images drawn by mermaid.ink, so they show in Colab, VS Code, JupyterLab
and on GitHub (they need an internet connection).

`RESET_MEMORY_ON_START=true` (the default in `.env.example`) wipes account
memory on every app start. Keep it on for rehearsals and the talk — otherwise repeated testing
on the same account (`borderline_wire`/`borderline_restart_demo` both use
`acct_2002`) accumulates enough escalation/decline history that triage
starts auto-declining them outright instead of routing to investigation.

### 2. Run LangGraph Studio

```bash
uv run langgraph dev
```

Opens a local Studio UI rendering the `fraud_guard` graph. Running the
specialist/aggregator nodes needs your model provider's key in `.env`
(`GEMINI_API_KEY` by default — see [Choosing a model](#choosing-a-model)).

`uv run langgraph dev --port <PORT>` starts a local API server and opens LangSmith's hosted
Studio UI (`smith.langchain.com/studio`) in your browser, pointed at that
local server — no LangSmith API key needed just to view/run the graph this
way. A LangSmith API key is only required separately if you also want run
traces (LLM calls, timings, inputs/outputs) to show up in the LangSmith
dashboard. Pass `--port` if the default port 2024 is already taken.

Studio loads `graph.py:studio_graph` rather than `graph.py:graph`
(`langgraph.json`) — the LangGraph API server manages its own persistence
and rejects a graph pre-compiled with a custom checkpointer/store, so
`studio_graph` is built without one. It's otherwise identical wiring;
Studio's own dev persistence lives in a local `.langgraph_api/` folder
instead of `checkpoints.sqlite`/`account_memory.sqlite`.

### 3. Enable LangSmith tracing (optional)

Off by default. To see every run's LLM calls, timings, and inputs/outputs
in the LangSmith dashboard (`smith.langchain.com`), grab a free API key from
there and set in `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=fraud-guard
```

Picked up automatically via `load_dotenv()` in `graph.py` — no code changes,
works for `langgraph dev`, the Streamlit UI, and `cli.py` alike. This is
separate from Studio (step 2 above), which renders the graph regardless of
whether tracing is on.

### 4. Run the review UI (Streamlit)

```bash
uv run streamlit run ui/app.py --server.port 8501
```

### 5. Run the CLI

A terminal companion to the Streamlit UI — same graph, same database files,
safe to run alongside it since both talk to the same checkpointed state.

```bash
uv run python cli.py submit clean_coffee        # submit a transaction, watch it investigate
uv run python cli.py pending                     # list transactions awaiting human review
uv run python cli.py review <thread_id> approve  # approve/decline/escalate a pending case
uv run python cli.py history                     # show all resolved transactions
```

`submit` takes any transaction ID — the four demo scenario names
(`clean_coffee`, `impossible_travel`, `borderline_wire`,
`borderline_restart_demo`), their `txn_00N` IDs, or literally anything else,
which deterministically synthesizes a plausible transaction (see "Any
transaction ID, not just a fixed menu" under **How it works** below). If the
transaction reaches `human_review`, `submit` prompts for a decision right
there in the terminal.

## Choosing a model

All LLM and embedding calls go through `core/llm.py: get_llm()` and
`core/embeddings.py: get_embeddings()`, which return LangChain models, so tool
calling (`create_react_agent`) and structured output work the same with
either provider. Settings in `.env`, read when a model is created:

| Setting | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `GEMINI_API_KEY` | (none) | needed when a provider is `gemini` |
| `OPENAI_API_KEY` | (none) | needed when a provider is `openai` |
| `LLM_MODEL` | `gemini-3.5-flash` / `gpt-4o-mini` | override the chat model for all agents and the aggregator |
| `EMBEDDING_PROVIDER` | same as `LLM_PROVIDER` | provider for the fraud-case search embeddings |
| `EMBEDDING_MODEL` | `models/gemini-embedding-001` / `text-embedding-3-small` | override the embedding model |

- Gemini runs with thinking off (short tool calls) and every call retries
  rate-limit errors with backoff, since the free tier allows only a few
  requests per minute and the three specialists run in parallel.
- Embeddings only feed an in-memory Chroma store rebuilt each run
  (`tools/mock_apis.py`), so switching provider needs no re-indexing.
- Gemini model names change often; on a `404 NOT_FOUND` or `503 UNAVAILABLE`
  set `LLM_MODEL` to another model listed in AI Studio.

## Notebooks

`notebooks/` teaches the project from scratch using its real code. Each
notebook opens with what you'll learn, time and cost, a flow diagram and a
table of its Parts, explains every step, and ends with things to try.

```bash
uv run jupyter lab notebooks/
```

| Notebook | What you'll learn | API key? |
|---|---|---|
| `00_start_here.ipynb` | The problem, tiered escalation, and every LangGraph building block on toy graphs: state, nodes, edges, conditional routing, parallel branches and reducers, interrupts + checkpoints, the store | no |
| `01_triage_rules.ipynb` | The scenarios and synthetic transactions, the mock lookups, triage scoring signal by signal, thresholds and routing, the account-memory penalty, and how much of 500 random transactions reaches the LLM | no |
| `02_specialist_agents.ipynb` | Tools, the fraud-case RAG search, the live MCP geolocation server, a ReAct agent step by step, all three specialists, the structured-output aggregator | yes |
| `03_full_graph.ipynb` | `build_graph()`, the drawn graph, the auto paths, the parallel investigation paused before `human_review`, resuming with a decision, the audit trail, any transaction ID | yes |
| `04_persistence_and_memory.ipynb` | A paused review surviving a rebuilt graph, the review queue and checkpoint history, long-term memory changing the next triage, Studio / app / CLI | yes |

- **Each notebook runs on its own** and uses its own database files in
  `.notebook_state/` (git-ignored), never the app's `checkpoints.sqlite` /
  `account_memory.sqlite`.
- Diagrams are Mermaid blocks, drawn by JupyterLab 4.1+ (installed by `--dev`).
- The notebooks are generated by `scripts/make_notebooks.py`; edit that file,
  then `uv run python scripts/make_notebooks.py notebooks` (this clears saved outputs).

## Demo script

1. Open Studio, walk through the graph diagram node by node.
2. Submit `clean_coffee` — watch it blip straight to `auto_approve`.
3. Submit `borderline_wire` — watch triage fan out to all three specialists
   simultaneously, fan into `aggregator`, then pause at `human_review`.
   Switch to the Streamlit UI, show the rationale, click **Approve**, watch
   `resolution` complete in Studio.
4. Submit `borderline_restart_demo`, let it reach `human_review`, then kill
   and restart the process — the pending case is still there. Studio persists
   this to its own local `.langgraph_api/` cache; the Streamlit UI/CLI persist
   to `checkpoints.sqlite` via our own `SqliteSaver` (see Studio note below).
   Approve it to finish. Point out that `transaction_analyst`'s writeup
   flagged the beneficiary via the `sanctions_check` tool — a new agent
   skill, added by giving one specialist one more tool, no graph changes.
5. Immediately resubmit `borderline_wire` (same account as step 4,
   `acct_2002`) and open its investigation trace — the triage score is
   visibly higher than the first time, because `triage` now remembers this
   account escalated before. That's the `SqliteStore` long-term memory, not
   the per-run checkpointer.
6. Recap: one node = one responsibility, conditional edges = business logic,
   the checkpointer buys per-run durability for free, the store buys
   cross-run memory for free.

Bonus MCP beat: point out that `identity_verifier`'s geolocation tool isn't
canned — it's served by a real MCP server (`mcp_server/geolocation_server.py`)
making a live HTTP call to ip-api.com. For `impossible_travel`, the resolved
IP genuinely geolocates to Nigeria, which is what makes the agent's writeup
convincing rather than scripted.

See `docs/superpowers/specs/2026-07-11-langgraph-fraud-demo-design.md` for
the full design and `docs/superpowers/plans/2026-07-11-langgraph-fraud-demo.md`
for the (unused) task-by-task TDD plan this was built from directly instead.

## The problem this solves

A real fraud pipeline is stuck between two bad options:

- **Rules only** — cheap and instant, but rigid. A fixed rule engine can't
  reason about context ("is a new device suspicious *given* this account's
  travel pattern?"), so it either misses fraud or blocks legitimate
  customers with hard thresholds.
- **LLM investigation on every transaction** — smarter and contextual, but
  slow and expensive. Running 3-4 LLM calls per transaction doesn't scale
  when 95%+ of transactions are unambiguous (a $6 coffee, an obviously
  cloned card halfway around the world in 10 minutes).

Fraud Guard's answer is **tiered escalation**: a free, instant rule engine
handles the transactions it can already tell apart with confidence, and only
the genuinely ambiguous middle band pays for a multi-agent LLM investigation
— which itself ends in a human decision rather than an autonomous one, since
nobody wants an LLM unilaterally freezing a legitimate wire transfer.

## How it works

```
                         ┌─────────────┐
                         │   ingest    │
                         └──────┬──────┘
                                ▼
                         ┌─────────────┐
                         │   triage    │  (deterministic rules, no LLM)
                         └──────┬──────┘
                    ┌───────────┼───────────┐
                    ▼            ▼           ▼
             auto_approve   auto_decline   investigate
                    │            │           │
                    │            │    ┌──────┼──────┐
                    │            │    ▼      ▼       ▼
                    │            │  analyst identity pattern   (parallel fan-out)
                    │            │    └──────┼──────┘
                    │            │           ▼
                    │            │      aggregator              (fan-in)
                    │            │           │
                    │            │    ┌──────┴──────┐
                    │            │    ▼             ▼
                    │            │  (score ok)   (still risky)
                    │            │    │             ▼
                    │            │    │       human_review        (interrupt_before,
                    │            │    │             │               waits for UI input)
                    │            │    │             ▼
                    └────────────┴────┴──────► resolution ──► END
```

Each box is one LangGraph node with one job:

| Node | Problem it solves | What it does |
|---|---|---|
| **`ingest`** | Every run needs a consistent starting point | Records the transaction into state and starts the audit trail |
| **`triage`** (`nodes/triage.py`) | Don't spend LLM calls on the transactions that are obvious (in a run of 500 random synthetic transactions, 91% were settled here) | Plain Python scoring against account history, device, merchant risk, and geo signals — no LLM. Routes to `auto_approve` (score < 0.30), `auto_decline` (score ≥ 0.65), or `investigate` (in between) |
| **`transaction_analyst`** | Is this amount/merchant actually unusual for *this* account, not just in the abstract? | ReAct agent with `account_history` + `merchant_risk_score` + `sanctions_check` tools |
| **`identity_verifier`** | Is the device and location consistent with the real account owner? | ReAct agent with `device_fingerprint` + a **live** `geolocation` tool — the only part of the demo that hits a real external API (see MCP section below) |
| **`pattern_detector`** | Does this resemble fraud patterns seen before, not just this account's own history? | ReAct agent with `account_history` + a RAG tool (`similar_fraud_cases`) searching a small Chroma store of past confirmed fraud cases |
| **`aggregator`** | Three independent opinions need to become *one* decision with a coherent explanation | LLM call with structured output (`AggregatorOutput`) combining all three findings into a `composite_score` + plain-English rationale. Routes to `human_review` (score ≥ 0.5) or straight to `resolution` |
| **`human_review`** | An LLM shouldn't autonomously block a legitimate $18k wire transfer, or wave through a borderline one, with nobody accountable | LangGraph `interrupt_before` node — execution genuinely pauses here, checkpointed to disk, until a human clicks Approve/Decline/Escalate in the Streamlit UI |
| **`resolution`** | Compliance needs one final answer and a full reasoning trail, not just a score | Combines `triage_decision`/`human_decision` into `final_decision`, closes out the audit log, and writes the decision to account memory (see below) |

The three specialist agents (`transaction_analyst`, `identity_verifier`,
`pattern_detector`) all run **in parallel** — LangGraph fans out from
`triage` to all three at once and fans back in at `aggregator`, since each
agent investigates an independent angle and none depends on another's
output. That parallelism, the conditional routing at `triage` and
`aggregator`, and the `human_review` interrupt are the three LangGraph
mechanics this demo exists to show off — see `core/specialist_factory.py`
for the shared node-building logic all three specialists are built from.

**Persistence**: every run is checkpointed to `checkpoints.sqlite` via
LangGraph's `SqliteSaver`, keyed by a unique thread ID per submission. This
is what lets a paused `human_review` survive killing and restarting the
whole process — the pending case is still there because it was never only
in memory.

**Long-term account memory**: separately from per-run checkpointing, a
`SqliteStore` (`account_memory.sqlite`) gives the graph memory that persists
*across* different transactions on the same account, not just within one
run. `resolution_node` writes `{final_decision, composite_score}` into
`(account_memory, account_id)` after every decision (`nodes/resolution.py`);
`triage_node` reads that account's history back via LangGraph's
`get_store()` and adds up to +0.3 to the score for prior escalations/declines
(`nodes/triage.py`). Concretely: `borderline_wire` and
`borderline_restart_demo` share the same account (`acct_2002`) — submit one,
escalate it, then submit the other, and its triage score will visibly be
higher than it would've been on a clean account, because triage now
remembers the account has a track record.

**A new agent skill**: `transaction_analyst` also has a `sanctions_check`
tool (`tools/mock_apis.py` → `tools/llm_tools.py`) that looks up a wire
transfer's `beneficiary_name` against a mock OFAC-style watchlist.
`borderline_wire`'s beneficiary is clean; `borderline_restart_demo`'s
(`"Silk Road Holdings Ltd"`) is flagged, and the agent leads its writeup
with that finding rather than burying it — a good moment to point out that
adding an agent capability is just adding a tool to a list, no graph changes
required.

**The MCP bonus**: `identity_verifier`'s `geolocation` tool isn't canned —
it's served by a real local MCP server (`mcp_server/geolocation_server.py`)
that the agent spawns and talks to via `langchain-mcp-adapters`, which makes
a live HTTP call to `ip-api.com`. For the `impossible_travel` scenario, the
resolved IP genuinely geolocates to Nigeria, which is what makes the agent's
writeup convincing rather than scripted. Everything else in the demo stays
synthetic/mock on purpose, so the rest of it runs offline and predictably.

**Any transaction ID, not just a fixed menu**: the UI takes free-text
input, not a scenario dropdown (`data/synthetic_transactions.py`). The four
demo scenarios above are still reachable by name or by their own
`transaction_id` (`txn_001`-`txn_004`) — that's what the quick-pick buttons
in the UI do — but typing *anything else* deterministically synthesizes a
plausible transaction by hashing the ID into a seeded RNG and drawing from a
larger pool of accounts/merchants/devices/geos, with roughly a 1-in-7 chance
of leaning risky. Same ID always reproduces the same transaction (so it's
still rehearsable), but it's no longer a closed catalog — type whatever
transaction ID an audience member shouts out and get a real investigation.

## Project structure

```
graph.py                      # StateGraph wiring: nodes, conditional edges, checkpointer
cli.py                        # terminal companion to the Streamlit UI
langgraph.json                # LangGraph Studio config
core/                          # shared infra used across agents/nodes/ui - no graph nodes live here
  llm.py                       # get_llm(): Gemini or OpenAI chat model (LLM_PROVIDER)
  embeddings.py                # get_embeddings(): Gemini or OpenAI embeddings
  state.py                     # TransactionState TypedDict
  audit.py                     # audit-log entry builders (info/tool_call/summary/...)
  specialist_factory.py        # shared lazy ReAct node builder for the 3 specialists
agents/                        # LLM ReAct agents only (tool-using specialists)
  transaction_analyst.py
  identity_verifier.py         # uses the live MCP geolocation tool
  pattern_detector.py
nodes/                         # deterministic / non-agent graph nodes
  ingest.py
  triage.py                   # deterministic rules + auto_approve/auto_decline
  aggregator.py                # structured-output fan-in node
  human_review.py              # interrupt_before target
  resolution.py
tools/
  mock_apis.py                 # account/device/geo/merchant/sanctions lookups + fraud-case RAG
  llm_tools.py                 # @tool wrappers for the specialist agents
  mcp_geolocation.py            # lazy client for the real geolocation MCP server
data/
  synthetic_transactions.py    # the 4 scripted scenarios (each has a real_ip too)
ui/
  logic.py                     # graph-driving functions (queue, resume)
  app.py                       # Streamlit rendering
  diagrams.py                   # hand-built SVG flow/architecture diagrams
mcp_server/
  geolocation_server.py         # FastMCP server calling ip-api.com for real geolocation
notebooks/                     # 00_start_here … 04_persistence_and_memory (see "Notebooks")
requirements.txt               # pinned from uv.lock, for pip / Colab (requirements-dev.txt adds Jupyter etc.)
scripts/
  make_notebooks.py            # generates notebooks/
tests/                         # pytest: provider selection (no API key needed)
docs/                          # talk materials (slides)
```

## Tests

```bash
uv run pytest
```

No API key needed: the tests check provider selection without calling a model.
