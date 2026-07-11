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
| **`resolution`** | Compliance needs one final answer and a full reasoning trail, not just a score | Combines `triage_decision`/`human_decision` into `final_decision` and closes out the audit log |

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
   finish.
5. Recap: one node = one responsibility, conditional edges = business logic,
   the checkpointer buys durability for free.

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
  mock_apis.py                 # account/device/geo/merchant lookups + fraud-case RAG
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
