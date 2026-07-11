# Fraud Guard — LangGraph Fintech Demo

A LangGraph demo built for a conference talk: a tiered fraud-detection
pipeline that only pays for expensive multi-agent LLM investigation on
borderline transactions, pauses for human review when risk stays high, and
survives a process restart mid-review thanks to checkpointing. The
`identity_verifier` agent's geolocation lookup is backed by a real local MCP
server hitting a live public IP-geolocation API — everything else stays
synthetic/mock so the rest of the demo runs offline and predictably.

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

## Architecture

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
