# Fraud Guard — LangGraph Fintech Demo

A LangGraph demo built for a conference talk: a tiered fraud-detection
pipeline that only pays for expensive multi-agent LLM investigation on
borderline transactions, pauses for human review when risk stays high, and
survives a process restart mid-review thanks to checkpointing. The
`identity_verifier` agent's geolocation lookup is backed by a real local MCP
server hitting a live public IP-geolocation API — everything else stays
synthetic/mock so the rest of the demo runs offline and predictably.

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
| **`triage`** (`agents/triage.py`) | Don't spend LLM calls on the 95% of transactions that are obvious | Plain Python scoring against account history, device, merchant risk, and geo signals — no LLM. Routes to `auto_approve` (score < 0.30), `auto_decline` (score ≥ 0.65), or `investigate` (in between) |
| **`transaction_analyst`** | Is this amount/merchant actually unusual for *this* account, not just in the abstract? | ReAct agent with `account_history` + `merchant_risk_score` tools |
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
mechanics this demo exists to show off — see `agents/specialist_factory.py`
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
`(account_memory, account_id)` after every decision (`agents/resolution.py`);
`triage_node` reads that account's history back via LangGraph's
`get_store()` and adds up to +0.3 to the score for prior escalations/declines
(`agents/triage.py`). Concretely: `borderline_wire` and
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

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in OPENAI_API_KEY
```

## Run LangGraph Studio

```bash
langgraph dev
```

Opens a local Studio UI rendering the `fraud_guard` graph. Requires
`OPENAI_API_KEY` in `.env` to actually execute specialist/aggregator nodes.

## Run the review UI

```bash
streamlit run ui/app.py
```

## Demo script

1. Open Studio, walk through the graph diagram node by node.
2. Submit `clean_coffee` — watch it blip straight to `auto_approve`.
3. Submit `borderline_wire` — watch triage fan out to all three specialists
   simultaneously, fan into `aggregator`, then pause at `human_review`.
   Switch to the Streamlit UI, show the rationale, click **Approve**, watch
   `resolution` complete in Studio.
4. Submit `borderline_restart_demo`, let it reach `human_review`, then kill
   and restart `langgraph dev` (and/or the Streamlit process) — the pending
   case is still there, checkpointed to `checkpoints.sqlite`. Approve it to
   finish. Point out that `transaction_analyst`'s writeup flagged the
   beneficiary via the `sanctions_check` tool — a new agent skill, added by
   giving one specialist one more tool, no graph changes.
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

## Project structure

```
state.py                      # TransactionState TypedDict
graph.py                      # StateGraph wiring: nodes, conditional edges, checkpointer
langgraph.json                # LangGraph Studio config
agents/
  ingest.py
  triage.py                   # deterministic rules + auto_approve/auto_decline
  specialist_factory.py       # shared lazy ReAct node builder
  transaction_analyst.py
  identity_verifier.py         # uses the live MCP geolocation tool
  pattern_detector.py
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
mcp_server/
  geolocation_server.py         # FastMCP server calling ip-api.com for real geolocation
```
