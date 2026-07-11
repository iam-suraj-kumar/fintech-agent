# LangGraph Fintech Fraud Detection Demo — Design

## Purpose

A live demo for a conference/meetup talk showing how LangGraph models a realistic
fintech fraud-detection pipeline: deterministic rule-based triage, conditional
routing, parallel multi-agent investigation, human-in-the-loop interrupts, and
checkpointed persistence. All data is synthetic; no real external APIs or
production data are involved. LLM calls use OpenAI (`ChatOpenAI`).

## Architecture: Tiered Escalation Pipeline

Every transaction hits a fast, cheap, deterministic triage node first.
Only borderline transactions pay for the expensive multi-agent LLM
investigation — this mirrors how a real fraud system is built and gives
the routing logic a real purpose in the demo narrative.

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

### Nodes

- **`ingest`** — accepts a raw transaction event, initializes state.
- **`triage`** — plain Python, no LLM: velocity check, amount thresholds, basic
  geo/device sanity checks. Fast and cheap; runs on every transaction. Produces
  `triage_score` and routes via conditional edge to `auto_approve`,
  `auto_decline`, or `investigate`.
- **`transaction_analyst`, `identity_verifier`, `pattern_detector`** — three
  parallel LangGraph nodes, each a small ReAct-style agent (OpenAI + tools).
  Added as concurrent out-edges from `investigate` so LangGraph fans them out
  at the same time. Each writes only its own state field.
- **`aggregator`** — LLM node (fan-in). Reads all three specialist findings
  plus the triage score, produces `composite_score` and a plain-English
  `aggregate_reasoning`. Conditional edge: score below threshold → straight to
  `resolution`; score at/above threshold → `human_review`.
- **`human_review`** — an `interrupt_before` node. Execution pauses here and
  state is checkpointed to disk. Resumes only when the UI writes
  `human_decision` into state and re-invokes the graph on the same
  `thread_id`.
- **`resolution`** — deterministic. Writes `final_decision` and appends the
  full reasoning trail to `audit_log`.

### State schema

```python
class TransactionState(TypedDict):
    transaction: dict                 # amount, merchant, account_id, device_id, ip, ts...
    triage_score: float
    triage_decision: Literal["auto_approve", "auto_decline", "investigate"]
    analyst_findings: str | None
    identity_findings: str | None
    pattern_findings: str | None
    composite_score: float | None
    aggregate_reasoning: str | None
    human_decision: Literal["approve", "decline", "escalate"] | None
    final_decision: str
    audit_log: list[str]              # appended by every node; streamed to the UI
```

### Checkpointing

`SqliteSaver`, keyed by `thread_id = transaction_id`. This is what allows the
process to be killed and restarted mid-`human_review` during the talk while
the pending case remains intact — the persistence payoff moment.

## Data & tools (all synthetic, no real APIs)

### Scenario generator (`data/synthetic_transactions.py`)

Four hand-scripted transactions chosen to hit each path predictably:

1. **Clean** — small in-network coffee purchase → `auto_approve` in one hop.
2. **Obvious fraud** — impossible travel (NYC charge, Lagos charge 10 minutes
   later) → `auto_decline` in one hop.
3. **Borderline #1** — large first-time international wire to a new
   beneficiary → routes to `investigate`; specialists mildly disagree;
   aggregator lands just above threshold → triggers `human_review`.
4. **Borderline #2** — reserved for the kill/restart-mid-interrupt demo beat.

### Mock tools (`tools/mock_apis.py`)

Callable by the three specialist agents, all in-memory/canned:

- `get_account_history(account_id)` — past transaction pattern, typical spend range
- `get_device_fingerprint(session_id)` — known vs. new device
- `get_geolocation(ip)` — country/city, distance from last known location
- `get_merchant_risk_score(merchant_id)` — canned risk tier lookup
- `search_similar_fraud_cases(transaction)` — small in-memory Chroma vector
  store seeded with a handful of embedded synthetic past-fraud cases (used by
  `pattern_detector`; gives the demo a legitimate RAG moment)

## Studio + UI integration

- **LangGraph Studio** — `langgraph.json` points at the compiled graph;
  `langgraph dev` renders the node diagram and highlights nodes live as they
  execute, including all three specialists lighting up simultaneously during
  fan-out. No custom code required. This is the primary "watch the graph
  move" visual for the talk.
- **Thin Streamlit UI** (`ui/app.py`) — a transaction queue table plus a
  detail pane. When a transaction reaches `human_review`, the pane shows the
  aggregator's rationale with Approve / Decline / Escalate buttons. Clicking
  one writes `human_decision` into that thread's state and re-invokes the
  graph on the same `thread_id`, resuming past the interrupt. Also streams
  `state["audit_log"]` live so the audience sees reasoning appear in real
  time, not just a static diagram.

## Demo script

1. Open Studio, walk through the graph diagram, ~30s per node.
2. Fire scenario 1 (clean) → blips straight to `auto_approve`. Fast and
   boring on purpose — sets up the contrast with what follows.
3. Fire scenario 3 (borderline) → Studio shows triage → simultaneous fan-out
   to all three specialists → aggregator → pause at `human_review`. Switch to
   Streamlit, show the rationale, click Approve → back to Studio, watch
   `resolution` complete.
4. Fire scenario 4, let it reach `human_review`, then **kill the process and
   restart it** → the pending case is still present in the UI, checkpointed
   to disk. Approve it, resume, done.
5. Closing recap: one node = one responsibility; conditional edges = business
   logic; the checkpointer buys durability for free.

## Project structure

```
fin-fraud-guard/
  state.py                      # TransactionState TypedDict
  graph.py                      # StateGraph wiring: nodes, conditional edges, checkpointer
  agents/
    triage.py                   # deterministic rules
    transaction_analyst.py
    identity_verifier.py
    pattern_detector.py
    aggregator.py
  tools/
    mock_apis.py                # account history, device, geo, merchant risk, fraud-case search
  data/
    synthetic_transactions.py   # the 4 scripted scenarios
  ui/
    app.py                      # Streamlit queue + human review + audit stream
  langgraph.json
  requirements.txt              # langgraph, langchain-openai, streamlit, chromadb
  README.md                     # setup + demo script
```

## Out of scope

- Real external APIs, production data, or real payment rails.
- Authentication/authorization for the Streamlit UI.
- Persisting audit logs anywhere beyond the SQLite checkpoint DB.
- Multi-user concurrent review (single reviewer assumed for the talk).
