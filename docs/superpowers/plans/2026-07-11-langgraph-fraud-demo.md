# LangGraph Fintech Fraud Detection Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable LangGraph demo ("Fraud Guard") that routes synthetic
fintech transactions through deterministic triage, conditional branching,
parallel multi-agent investigation, a human-in-the-loop interrupt, and
checkpointed persistence — viewable in LangGraph Studio and a thin Streamlit
review UI, for a conference talk.

**Architecture:** A single `StateGraph` over a shared `TransactionState`.
Every transaction hits a cheap deterministic `triage` node first; only
borderline transactions fan out to three parallel LLM specialist agents,
which fan back into an `aggregator` that either resolves automatically or
pauses at a `human_review` interrupt for a Streamlit reviewer to approve.
`SqliteSaver` checkpoints every run to disk so a paused review survives a
process restart.

**Tech Stack:** Python 3.11+, LangGraph (`langgraph`, `langgraph-checkpoint-sqlite`),
LangChain (`langchain-core`, `langchain-openai`), OpenAI (`gpt-4o-mini`) as the
LLM behind every agent node, Chroma (`chromadb`) for the in-memory fraud-case
similarity search, Streamlit for the review UI, pytest for tests.

## Global Constraints

- LLM provider is OpenAI (`ChatOpenAI`), not Anthropic — every agent node uses `gpt-4o-mini` by default.
- No real external APIs or production data — all account/device/geo/merchant data is synthetic and canned.
- All automated tests must run offline: no network calls, no `OPENAI_API_KEY` required at import time or test time. LLM/embedding clients are constructed lazily (only when a node actually executes) and are monkeypatched in tests.
- Triage thresholds: `auto_decline` if score ≥ 0.65, `investigate` if score ≥ 0.30, else `auto_approve`.
- Aggregator threshold: composite score ≥ 0.5 routes to `human_review`, else straight to `resolution`.
- Checkpointer is `SqliteSaver` writing to a local file (`checkpoints.sqlite` by default, overridable via `CHECKPOINT_DB_PATH`), not in-memory — persistence across process restart is a required demo beat.
- Every module that constructs an LLM/embeddings client must defer that construction until the node function is actually invoked, never at import time.

---

## Task 1: Project scaffolding & dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `agents/__init__.py`
- Create: `tools/__init__.py`
- Create: `data/__init__.py`
- Create: `ui/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: a project root where `pytest` (run from the root) can resolve `import state`, `from tools.mock_apis import ...`, `from agents.triage import ...`, `from data.synthetic_transactions import ...`, `from ui.logic import ...` without a `src/` layout or installed package.

- [ ] **Step 1: Write `requirements.txt`**

```
langgraph>=0.2.60
langgraph-checkpoint-sqlite>=2.0.0
langchain-core>=0.3.0
langchain-openai>=0.2.0
langchain-chroma>=0.1.4
chromadb>=0.5.0
streamlit>=1.38.0
pydantic>=2.7.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Write `.env.example`**

```
OPENAI_API_KEY=sk-...
CHECKPOINT_DB_PATH=checkpoints.sqlite
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.env
checkpoints.sqlite
.pytest_cache/
.chroma/
```

- [ ] **Step 4: Write `pyproject.toml`**

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 5: Create empty package `__init__.py` files**

```bash
touch agents/__init__.py tools/__init__.py data/__init__.py ui/__init__.py tests/__init__.py
```

- [ ] **Step 6: Install dependencies and verify pytest runs**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest --collect-only
```

Expected: `collected 0 items` (no test files yet), no import errors.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore pyproject.toml agents/__init__.py tools/__init__.py data/__init__.py ui/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure and dependencies"
```

---

## Task 2: State schema

**Files:**
- Create: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces: `TransactionState` (TypedDict) with keys `transaction, triage_score, triage_decision, analyst_findings, identity_findings, pattern_findings, composite_score, aggregate_reasoning, human_decision, final_decision, audit_log`; `new_state(transaction: dict) -> TransactionState` factory with sensible defaults.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
from state import new_state


def test_new_state_sets_transaction_and_defaults():
    state = new_state({"transaction_id": "txn_1", "amount": 10.0})

    assert state["transaction"] == {"transaction_id": "txn_1", "amount": 10.0}
    assert state["triage_score"] == 0.0
    assert state["triage_decision"] == "auto_approve"
    assert state["analyst_findings"] is None
    assert state["identity_findings"] is None
    assert state["pattern_findings"] is None
    assert state["composite_score"] is None
    assert state["aggregate_reasoning"] is None
    assert state["human_decision"] is None
    assert state["final_decision"] == ""
    assert state["audit_log"] == []


def test_new_state_returns_independent_audit_logs():
    state_a = new_state({"transaction_id": "txn_a"})
    state_b = new_state({"transaction_id": "txn_b"})

    state_a["audit_log"].append("a")

    assert state_b["audit_log"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Write `state.py`**

```python
from typing import Literal, TypedDict


class TransactionState(TypedDict):
    transaction: dict
    triage_score: float
    triage_decision: Literal["auto_approve", "auto_decline", "investigate"]
    analyst_findings: str | None
    identity_findings: str | None
    pattern_findings: str | None
    composite_score: float | None
    aggregate_reasoning: str | None
    human_decision: Literal["approve", "decline", "escalate"] | None
    final_decision: str
    audit_log: list[str]


def new_state(transaction: dict) -> TransactionState:
    return {
        "transaction": transaction,
        "triage_score": 0.0,
        "triage_decision": "auto_approve",
        "analyst_findings": None,
        "identity_findings": None,
        "pattern_findings": None,
        "composite_score": None,
        "aggregate_reasoning": None,
        "human_decision": None,
        "final_decision": "",
        "audit_log": [],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: add TransactionState schema and new_state factory"
```

---

## Task 3: Mock APIs — deterministic lookups

**Files:**
- Create: `tools/mock_apis.py`
- Test: `tests/test_mock_apis.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `get_account_history(account_id: str) -> dict` (keys `typical_range: tuple[float, float]`, `country: str`, `avg_txn_count_per_week: int`), `get_device_fingerprint(device_id: str) -> dict` (keys `known: bool`, `first_seen_days_ago: int`), `get_geolocation(ip: str) -> dict` (keys `country: str`, `city: str`), `get_merchant_risk_score(merchant_id: str) -> dict` (keys `tier: str`, `score: float`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mock_apis.py
from tools.mock_apis import (
    get_account_history,
    get_device_fingerprint,
    get_geolocation,
    get_merchant_risk_score,
)


def test_get_account_history_known_account():
    result = get_account_history("acct_1001")
    assert result["typical_range"] == (5, 150)
    assert result["country"] == "US"


def test_get_account_history_unknown_account_returns_fallback():
    result = get_account_history("acct_does_not_exist")
    assert result["typical_range"] == (0, 100)


def test_get_device_fingerprint_known_device():
    result = get_device_fingerprint("dev_known_1")
    assert result["known"] is True


def test_get_device_fingerprint_unknown_device_returns_fallback():
    result = get_device_fingerprint("dev_does_not_exist")
    assert result["known"] is False


def test_get_geolocation_known_ip():
    result = get_geolocation("ip_ng_lagos")
    assert result["country"] == "NG"
    assert result["city"] == "Lagos"


def test_get_geolocation_unknown_ip_returns_fallback():
    result = get_geolocation("ip_does_not_exist")
    assert result["country"] == "US"
    assert result["city"] == "Unknown"


def test_get_merchant_risk_score_known_merchant():
    result = get_merchant_risk_score("merch_wire_intl_1")
    assert result["tier"] == "high"
    assert result["score"] == 0.72


def test_get_merchant_risk_score_unknown_merchant_returns_fallback():
    result = get_merchant_risk_score("merch_does_not_exist")
    assert result["tier"] == "medium"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mock_apis.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.mock_apis'`

- [ ] **Step 3: Write `tools/mock_apis.py`**

```python
ACCOUNT_HISTORY = {
    "acct_1001": {"typical_range": (5, 150), "country": "US", "avg_txn_count_per_week": 12},
    "acct_2002": {"typical_range": (500, 5000), "country": "US", "avg_txn_count_per_week": 3},
    "acct_3003": {"typical_range": (10, 80), "country": "US", "avg_txn_count_per_week": 20},
}

DEVICE_FINGERPRINTS = {
    "dev_known_1": {"known": True, "first_seen_days_ago": 412},
    "dev_new_1": {"known": False, "first_seen_days_ago": 0},
}

GEOLOCATIONS = {
    "ip_us_ny": {"country": "US", "city": "New York"},
    "ip_ng_lagos": {"country": "NG", "city": "Lagos"},
    "ip_us_sf": {"country": "US", "city": "San Francisco"},
}

MERCHANT_RISK = {
    "merch_coffee_1": {"tier": "low", "score": 0.05},
    "merch_wire_intl_1": {"tier": "high", "score": 0.72},
    "merch_electronics_1": {"tier": "medium", "score": 0.35},
}


def get_account_history(account_id: str) -> dict:
    return ACCOUNT_HISTORY.get(
        account_id,
        {"typical_range": (0, 100), "country": "US", "avg_txn_count_per_week": 5},
    )


def get_device_fingerprint(device_id: str) -> dict:
    return DEVICE_FINGERPRINTS.get(device_id, {"known": False, "first_seen_days_ago": 0})


def get_geolocation(ip: str) -> dict:
    return GEOLOCATIONS.get(ip, {"country": "US", "city": "Unknown"})


def get_merchant_risk_score(merchant_id: str) -> dict:
    return MERCHANT_RISK.get(merchant_id, {"tier": "medium", "score": 0.3})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mock_apis.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/mock_apis.py tests/test_mock_apis.py
git commit -m "feat: add deterministic mock lookup APIs"
```

---

## Task 4: Fraud case similarity search

**Files:**
- Modify: `tools/mock_apis.py`
- Test: `tests/test_mock_apis.py`

**Interfaces:**
- Consumes: nothing external (lazily builds its own in-memory Chroma store on first call).
- Produces: `search_similar_fraud_cases(query: str, k: int = 2) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_mock_apis.py
import tools.mock_apis as mock_apis


class _FakeDoc:
    def __init__(self, page_content):
        self.page_content = page_content


class _FakeStore:
    def __init__(self):
        self.queries = []

    def similarity_search(self, query, k):
        self.queries.append((query, k))
        return [_FakeDoc("case A"), _FakeDoc("case B")][:k]


def test_search_similar_fraud_cases_returns_page_contents(monkeypatch):
    fake_store = _FakeStore()
    monkeypatch.setattr(mock_apis, "_get_store", lambda: fake_store)

    result = mock_apis.search_similar_fraud_cases("suspicious wire transfer", k=2)

    assert result == ["case A", "case B"]
    assert fake_store.queries == [("suspicious wire transfer", 2)]


def test_search_similar_fraud_cases_respects_k(monkeypatch):
    fake_store = _FakeStore()
    monkeypatch.setattr(mock_apis, "_get_store", lambda: fake_store)

    result = mock_apis.search_similar_fraud_cases("test", k=1)

    assert result == ["case A"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mock_apis.py -v -k fraud_cases`
Expected: FAIL with `AttributeError: module 'tools.mock_apis' has no attribute 'search_similar_fraud_cases'`

- [ ] **Step 3: Add to `tools/mock_apis.py`**

```python
FRAUD_CASE_TEXTS = [
    "Card-not-present purchase for $2,340 at an electronics merchant the "
    "cardholder never used before, from a new device, immediately followed "
    "by a request to ship to a freight-forwarding address.",
    "International wire transfer of $18,000 to a newly added beneficiary "
    "within 10 minutes of the beneficiary being added to the account.",
    "Series of small $1-3 test transactions at unrelated online merchants "
    "within a 2-minute window, typical of card validation/testing fraud.",
    "Account login from a new device and new country followed within "
    "minutes by a large balance transfer.",
]

_store = None


def _get_store():
    global _store
    if _store is None:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        _store = Chroma.from_texts(FRAUD_CASE_TEXTS, OpenAIEmbeddings())
    return _store


def search_similar_fraud_cases(query: str, k: int = 2) -> list[str]:
    store = _get_store()
    docs = store.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mock_apis.py -v`
Expected: PASS (10 tests total)

- [ ] **Step 5: Commit**

```bash
git add tools/mock_apis.py tests/test_mock_apis.py
git commit -m "feat: add lazy Chroma-backed similar fraud case search"
```

---

## Task 5: LLM tool wrappers

**Files:**
- Create: `tools/llm_tools.py`
- Test: `tests/test_llm_tools.py`

**Interfaces:**
- Consumes: `tools.mock_apis.{get_account_history, get_device_fingerprint, get_geolocation, get_merchant_risk_score, search_similar_fraud_cases}`.
- Produces: `@tool`-decorated callables `account_history`, `device_fingerprint`, `geolocation`, `merchant_risk_score`, `similar_fraud_cases`, each invokable via `.invoke({...})` and carrying a non-empty `.description`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_tools.py
import tools.llm_tools as llm_tools


def test_account_history_tool_delegates_and_has_description(monkeypatch):
    monkeypatch.setattr(llm_tools, "_get_account_history", lambda account_id: {"ok": account_id})

    result = llm_tools.account_history.invoke({"account_id": "acct_1001"})

    assert result == {"ok": "acct_1001"}
    assert llm_tools.account_history.description


def test_device_fingerprint_tool_delegates(monkeypatch):
    monkeypatch.setattr(llm_tools, "_get_device_fingerprint", lambda device_id: {"ok": device_id})

    result = llm_tools.device_fingerprint.invoke({"device_id": "dev_1"})

    assert result == {"ok": "dev_1"}


def test_geolocation_tool_delegates(monkeypatch):
    monkeypatch.setattr(llm_tools, "_get_geolocation", lambda ip: {"ok": ip})

    result = llm_tools.geolocation.invoke({"ip": "ip_us_ny"})

    assert result == {"ok": "ip_us_ny"}


def test_merchant_risk_score_tool_delegates(monkeypatch):
    monkeypatch.setattr(llm_tools, "_get_merchant_risk_score", lambda merchant_id: {"ok": merchant_id})

    result = llm_tools.merchant_risk_score.invoke({"merchant_id": "merch_1"})

    assert result == {"ok": "merch_1"}


def test_similar_fraud_cases_tool_delegates(monkeypatch):
    monkeypatch.setattr(llm_tools, "_search_similar_fraud_cases", lambda description: [description])

    result = llm_tools.similar_fraud_cases.invoke({"description": "wire fraud"})

    assert result == ["wire fraud"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.llm_tools'`

- [ ] **Step 3: Write `tools/llm_tools.py`**

```python
from langchain_core.tools import tool

from tools.mock_apis import (
    get_account_history as _get_account_history,
    get_device_fingerprint as _get_device_fingerprint,
    get_geolocation as _get_geolocation,
    get_merchant_risk_score as _get_merchant_risk_score,
    search_similar_fraud_cases as _search_similar_fraud_cases,
)


@tool
def account_history(account_id: str) -> dict:
    """Look up an account's typical spending pattern: amount range, home country, and average transactions per week."""
    return _get_account_history(account_id)


@tool
def device_fingerprint(device_id: str) -> dict:
    """Look up whether a device ID is known for the account and how long ago it was first seen."""
    return _get_device_fingerprint(device_id)


@tool
def geolocation(ip: str) -> dict:
    """Look up the country and city associated with an IP address."""
    return _get_geolocation(ip)


@tool
def merchant_risk_score(merchant_id: str) -> dict:
    """Look up a merchant's risk tier (low/medium/high) and numeric risk score."""
    return _get_merchant_risk_score(merchant_id)


@tool
def similar_fraud_cases(description: str) -> list[str]:
    """Search a database of past confirmed fraud cases for ones textually similar to the given transaction description."""
    return _search_similar_fraud_cases(description)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_tools.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/llm_tools.py tests/test_llm_tools.py
git commit -m "feat: add LLM-callable tool wrappers around mock APIs"
```

---

## Task 6: Synthetic transaction scenarios

**Files:**
- Create: `data/synthetic_transactions.py`
- Test: `tests/test_synthetic_transactions.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SCENARIOS: dict[str, dict]` with keys `clean_coffee`, `impossible_travel`, `borderline_wire`, `borderline_restart_demo`; `get_scenario(name: str) -> dict` returning an independent copy, raising `KeyError` for unknown names.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_synthetic_transactions.py
import pytest

from data.synthetic_transactions import SCENARIOS, get_scenario


def test_all_four_scenarios_exist():
    assert set(SCENARIOS.keys()) == {
        "clean_coffee",
        "impossible_travel",
        "borderline_wire",
        "borderline_restart_demo",
    }


def test_get_scenario_returns_expected_transaction_id():
    assert get_scenario("clean_coffee")["transaction_id"] == "txn_001"
    assert get_scenario("impossible_travel")["transaction_id"] == "txn_002"
    assert get_scenario("borderline_wire")["transaction_id"] == "txn_003"
    assert get_scenario("borderline_restart_demo")["transaction_id"] == "txn_004"


def test_get_scenario_returns_independent_copy():
    first = get_scenario("clean_coffee")
    first["amount"] = 999999

    assert get_scenario("clean_coffee")["amount"] != 999999


def test_get_scenario_unknown_name_raises():
    with pytest.raises(KeyError):
        get_scenario("does_not_exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_synthetic_transactions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.synthetic_transactions'`

- [ ] **Step 3: Write `data/synthetic_transactions.py`**

```python
from datetime import datetime, timezone

SCENARIOS = {
    "clean_coffee": {
        "transaction_id": "txn_001",
        "account_id": "acct_3003",
        "amount": 6.50,
        "merchant_id": "merch_coffee_1",
        "device_id": "dev_known_1",
        "ip": "ip_us_ny",
        "timestamp": datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc).isoformat(),
        "type": "card_present",
    },
    "impossible_travel": {
        "transaction_id": "txn_002",
        "account_id": "acct_1001",
        "amount": 340.00,
        "merchant_id": "merch_electronics_1",
        "device_id": "dev_new_1",
        "ip": "ip_ng_lagos",
        "timestamp": datetime(2026, 7, 11, 14, 10, tzinfo=timezone.utc).isoformat(),
        "type": "card_not_present",
        "prior_ip": "ip_us_ny",
        "prior_timestamp": datetime(2026, 7, 11, 14, 0, tzinfo=timezone.utc).isoformat(),
    },
    "borderline_wire": {
        "transaction_id": "txn_003",
        "account_id": "acct_2002",
        "amount": 18000.00,
        "merchant_id": "merch_wire_intl_1",
        "device_id": "dev_known_1",
        "ip": "ip_us_sf",
        "timestamp": datetime(2026, 7, 11, 16, 30, tzinfo=timezone.utc).isoformat(),
        "type": "wire_transfer",
        "beneficiary_is_new": True,
    },
    "borderline_restart_demo": {
        "transaction_id": "txn_004",
        "account_id": "acct_2002",
        "amount": 9500.00,
        "merchant_id": "merch_wire_intl_1",
        "device_id": "dev_new_1",
        "ip": "ip_us_sf",
        "timestamp": datetime(2026, 7, 11, 17, 0, tzinfo=timezone.utc).isoformat(),
        "type": "wire_transfer",
        "beneficiary_is_new": True,
    },
}


def get_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {name}")
    return dict(SCENARIOS[name])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_synthetic_transactions.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add data/synthetic_transactions.py tests/test_synthetic_transactions.py
git commit -m "feat: add scripted synthetic transaction scenarios"
```

---

## Task 7: Ingest node

**Files:**
- Create: `agents/ingest.py`
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `state.TransactionState`.
- Produces: `ingest_node(state: TransactionState) -> dict` returning `{"audit_log": [...]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest.py
from agents.ingest import ingest_node
from state import new_state


def test_ingest_node_appends_audit_log_entry():
    state = new_state({"transaction_id": "txn_001"})

    result = ingest_node(state)

    assert result["audit_log"] == ["ingest: received transaction txn_001"]


def test_ingest_node_handles_missing_transaction_id():
    state = new_state({})

    result = ingest_node(state)

    assert result["audit_log"] == ["ingest: received transaction unknown"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.ingest'`

- [ ] **Step 3: Write `agents/ingest.py`**

```python
from state import TransactionState


def ingest_node(state: TransactionState) -> dict:
    txn_id = state["transaction"].get("transaction_id", "unknown")
    return {"audit_log": state["audit_log"] + [f"ingest: received transaction {txn_id}"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add agents/ingest.py tests/test_ingest.py
git commit -m "feat: add ingest node"
```

---

## Task 8: Triage node, auto-approve/decline nodes, and routing

**Files:**
- Create: `agents/triage.py`
- Test: `tests/test_triage.py`

**Interfaces:**
- Consumes: `state.TransactionState`, `tools.mock_apis.{get_account_history, get_device_fingerprint, get_geolocation, get_merchant_risk_score}`, `data.synthetic_transactions.get_scenario`.
- Produces: `triage_node(state) -> dict` (sets `triage_score`, `triage_decision`, appends `audit_log`); `route_after_triage(state) -> list[str]` (returns `["auto_approve"]`, `["auto_decline"]`, or `["transaction_analyst", "identity_verifier", "pattern_detector"]`); `auto_approve_node(state) -> dict`; `auto_decline_node(state) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_triage.py
from agents.triage import (
    auto_approve_node,
    auto_decline_node,
    route_after_triage,
    triage_node,
)
from data.synthetic_transactions import get_scenario
from state import new_state


def test_clean_coffee_auto_approves():
    state = new_state(get_scenario("clean_coffee"))

    result = triage_node(state)

    assert result["triage_decision"] == "auto_approve"
    assert result["triage_score"] < 0.30


def test_impossible_travel_auto_declines():
    state = new_state(get_scenario("impossible_travel"))

    result = triage_node(state)

    assert result["triage_decision"] == "auto_decline"
    assert result["triage_score"] >= 0.65


def test_borderline_wire_routes_to_investigate():
    state = new_state(get_scenario("borderline_wire"))

    result = triage_node(state)

    assert result["triage_decision"] == "investigate"
    assert 0.30 <= result["triage_score"] < 0.65


def test_borderline_restart_demo_routes_to_investigate():
    state = new_state(get_scenario("borderline_restart_demo"))

    result = triage_node(state)

    assert result["triage_decision"] == "investigate"
    assert 0.30 <= result["triage_score"] < 0.65


def test_triage_node_appends_audit_log():
    state = new_state(get_scenario("clean_coffee"))

    result = triage_node(state)

    assert result["audit_log"][0].startswith("triage: score=")


def test_route_after_triage_auto_approve():
    state = new_state({})
    state["triage_decision"] = "auto_approve"
    assert route_after_triage(state) == ["auto_approve"]


def test_route_after_triage_auto_decline():
    state = new_state({})
    state["triage_decision"] = "auto_decline"
    assert route_after_triage(state) == ["auto_decline"]


def test_route_after_triage_investigate_fans_out():
    state = new_state({})
    state["triage_decision"] = "investigate"
    assert route_after_triage(state) == [
        "transaction_analyst",
        "identity_verifier",
        "pattern_detector",
    ]


def test_auto_approve_node_appends_audit_log():
    state = new_state({})
    result = auto_approve_node(state)
    assert result["audit_log"] == ["auto_approve: triage score below investigation threshold"]


def test_auto_decline_node_appends_audit_log():
    state = new_state({})
    result = auto_decline_node(state)
    assert result["audit_log"] == ["auto_decline: triage score indicates high-confidence fraud"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_triage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.triage'`

- [ ] **Step 3: Write `agents/triage.py`**

```python
from state import TransactionState
from tools.mock_apis import (
    get_account_history,
    get_device_fingerprint,
    get_geolocation,
    get_merchant_risk_score,
)

AUTO_DECLINE_THRESHOLD = 0.65
INVESTIGATE_THRESHOLD = 0.30


def _compute_triage_score(transaction: dict) -> float:
    score = 0.0

    account = get_account_history(transaction["account_id"])
    _, high = account["typical_range"]
    if transaction["amount"] > high * 3:
        score += 0.35
    elif transaction["amount"] > high:
        score += 0.15

    device = get_device_fingerprint(transaction["device_id"])
    if not device["known"]:
        score += 0.15

    merchant = get_merchant_risk_score(transaction["merchant_id"])
    score += merchant["score"] * 0.2

    if transaction.get("beneficiary_is_new"):
        score += 0.15

    prior_ip = transaction.get("prior_ip")
    if prior_ip and prior_ip != transaction["ip"]:
        prior_country = get_geolocation(prior_ip)["country"]
        current_country = get_geolocation(transaction["ip"])["country"]
        if prior_country != current_country:
            score += 0.55

    return min(score, 1.0)


def triage_node(state: TransactionState) -> dict:
    transaction = state["transaction"]
    score = _compute_triage_score(transaction)

    if score >= AUTO_DECLINE_THRESHOLD:
        decision = "auto_decline"
    elif score >= INVESTIGATE_THRESHOLD:
        decision = "investigate"
    else:
        decision = "auto_approve"

    return {
        "triage_score": score,
        "triage_decision": decision,
        "audit_log": state["audit_log"] + [f"triage: score={score:.2f} decision={decision}"],
    }


def route_after_triage(state: TransactionState) -> list[str]:
    decision = state["triage_decision"]
    if decision == "investigate":
        return ["transaction_analyst", "identity_verifier", "pattern_detector"]
    return [decision]


def auto_approve_node(state: TransactionState) -> dict:
    return {
        "audit_log": state["audit_log"] + ["auto_approve: triage score below investigation threshold"]
    }


def auto_decline_node(state: TransactionState) -> dict:
    return {
        "audit_log": state["audit_log"] + ["auto_decline: triage score indicates high-confidence fraud"]
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_triage.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add agents/triage.py tests/test_triage.py
git commit -m "feat: add deterministic triage node and post-triage routing"
```

---

## Task 9: Specialist agent factory

**Files:**
- Create: `agents/specialist_factory.py`
- Test: `tests/test_specialist_factory.py`

**Interfaces:**
- Consumes: `state.TransactionState`, `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.create_react_agent`.
- Produces: `make_specialist_node(name: str, state_key: str, tools: list, system_prompt: str, model: str = "gpt-4o-mini") -> Callable[[TransactionState], dict]`. The returned node writes `{state_key: <finding text>, "audit_log": [...]}` and defers LLM/agent construction until first invocation.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_specialist_factory.py
from agents.specialist_factory import make_specialist_node
from state import new_state


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeAgent:
    def __init__(self):
        self.invoke_calls = []

    def invoke(self, payload):
        self.invoke_calls.append(payload)
        return {"messages": [_FakeMessage("finding text")]}


def test_specialist_node_writes_state_key_and_audit_log(monkeypatch):
    fake_agent = _FakeAgent()
    monkeypatch.setattr("agents.specialist_factory.ChatOpenAI", lambda **kwargs: object())
    monkeypatch.setattr(
        "agents.specialist_factory.create_react_agent",
        lambda llm, tools, prompt: fake_agent,
    )

    node = make_specialist_node(
        name="pattern_detector",
        state_key="pattern_findings",
        tools=[],
        system_prompt="find patterns",
    )
    state = new_state({"transaction_id": "txn_1"})

    result = node(state)

    assert result["pattern_findings"] == "finding text"
    assert result["audit_log"] == ["pattern_detector: finding text"]
    assert len(fake_agent.invoke_calls) == 1


def test_specialist_node_constructs_agent_lazily_only_once(monkeypatch):
    construction_count = {"n": 0}

    def fake_create_react_agent(llm, tools, prompt):
        construction_count["n"] += 1
        return _FakeAgent()

    monkeypatch.setattr("agents.specialist_factory.ChatOpenAI", lambda **kwargs: object())
    monkeypatch.setattr("agents.specialist_factory.create_react_agent", fake_create_react_agent)

    node = make_specialist_node(
        name="pattern_detector", state_key="pattern_findings", tools=[], system_prompt="x"
    )

    assert construction_count["n"] == 0

    node(new_state({"transaction_id": "txn_1"}))
    node(new_state({"transaction_id": "txn_2"}))

    assert construction_count["n"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_specialist_factory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.specialist_factory'`

- [ ] **Step 3: Write `agents/specialist_factory.py`**

```python
from typing import Callable

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from state import TransactionState

DEFAULT_MODEL = "gpt-4o-mini"


def make_specialist_node(
    name: str,
    state_key: str,
    tools: list,
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> Callable[[TransactionState], dict]:
    agent_holder: dict = {}

    def _get_agent():
        if "agent" not in agent_holder:
            llm = ChatOpenAI(model=model, temperature=0)
            agent_holder["agent"] = create_react_agent(llm, tools, prompt=system_prompt)
        return agent_holder["agent"]

    def node(state: TransactionState) -> dict:
        agent = _get_agent()
        transaction = state["transaction"]
        result = agent.invoke(
            {"messages": [("user", f"Investigate this transaction: {transaction}")]}
        )
        finding = result["messages"][-1].content
        return {
            state_key: finding,
            "audit_log": state["audit_log"] + [f"{name}: {finding}"],
        }

    return node
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_specialist_factory.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add agents/specialist_factory.py tests/test_specialist_factory.py
git commit -m "feat: add lazily-initialized specialist agent node factory"
```

---

## Task 10: Transaction analyst agent

**Files:**
- Create: `agents/transaction_analyst.py`
- Test: `tests/test_transaction_analyst.py`

**Interfaces:**
- Consumes: `agents.specialist_factory.make_specialist_node`, `tools.llm_tools.{account_history, merchant_risk_score}`.
- Produces: `transaction_analyst_node: Callable[[TransactionState], dict]` writing to `analyst_findings`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transaction_analyst.py
from unittest.mock import MagicMock

from agents.transaction_analyst import transaction_analyst_node
from state import new_state


def test_transaction_analyst_node_uses_expected_tools_and_state_key(monkeypatch):
    captured = {}

    def fake_create_react_agent(llm, tools, prompt):
        captured["tools"] = tools
        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"messages": [MagicMock(content="looks fine")]}
        return fake_agent

    monkeypatch.setattr("agents.specialist_factory.ChatOpenAI", lambda **kwargs: object())
    monkeypatch.setattr("agents.specialist_factory.create_react_agent", fake_create_react_agent)

    state = new_state({"transaction_id": "txn_1"})
    result = transaction_analyst_node(state)

    assert result["analyst_findings"] == "looks fine"
    assert [t.name for t in captured["tools"]] == ["account_history", "merchant_risk_score"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transaction_analyst.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.transaction_analyst'`

- [ ] **Step 3: Write `agents/transaction_analyst.py`**

```python
from agents.specialist_factory import make_specialist_node
from tools.llm_tools import account_history, merchant_risk_score

SYSTEM_PROMPT = (
    "You are a transaction analyst investigating a potentially fraudulent "
    "financial transaction. Use the account history and merchant risk tools "
    "to check whether the amount and merchant are consistent with the "
    "account's typical behavior. Summarize your assessment in 2-3 sentences."
)

transaction_analyst_node = make_specialist_node(
    name="transaction_analyst",
    state_key="analyst_findings",
    tools=[account_history, merchant_risk_score],
    system_prompt=SYSTEM_PROMPT,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transaction_analyst.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add agents/transaction_analyst.py tests/test_transaction_analyst.py
git commit -m "feat: add transaction analyst specialist agent"
```

---

## Task 11: Identity verifier agent

**Files:**
- Create: `agents/identity_verifier.py`
- Test: `tests/test_identity_verifier.py`

**Interfaces:**
- Consumes: `agents.specialist_factory.make_specialist_node`, `tools.llm_tools.{device_fingerprint, geolocation}`.
- Produces: `identity_verifier_node: Callable[[TransactionState], dict]` writing to `identity_findings`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identity_verifier.py
from unittest.mock import MagicMock

from agents.identity_verifier import identity_verifier_node
from state import new_state


def test_identity_verifier_node_uses_expected_tools_and_state_key(monkeypatch):
    captured = {}

    def fake_create_react_agent(llm, tools, prompt):
        captured["tools"] = tools
        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"messages": [MagicMock(content="device is new")]}
        return fake_agent

    monkeypatch.setattr("agents.specialist_factory.ChatOpenAI", lambda **kwargs: object())
    monkeypatch.setattr("agents.specialist_factory.create_react_agent", fake_create_react_agent)

    state = new_state({"transaction_id": "txn_1"})
    result = identity_verifier_node(state)

    assert result["identity_findings"] == "device is new"
    assert [t.name for t in captured["tools"]] == ["device_fingerprint", "geolocation"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_identity_verifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.identity_verifier'`

- [ ] **Step 3: Write `agents/identity_verifier.py`**

```python
from agents.specialist_factory import make_specialist_node
from tools.llm_tools import device_fingerprint, geolocation

SYSTEM_PROMPT = (
    "You are an identity and device verification specialist. Use the device "
    "fingerprint and geolocation tools to assess whether the device and "
    "location used for this transaction are consistent with legitimate "
    "account activity. Summarize your assessment in 2-3 sentences."
)

identity_verifier_node = make_specialist_node(
    name="identity_verifier",
    state_key="identity_findings",
    tools=[device_fingerprint, geolocation],
    system_prompt=SYSTEM_PROMPT,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_identity_verifier.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add agents/identity_verifier.py tests/test_identity_verifier.py
git commit -m "feat: add identity verifier specialist agent"
```

---

## Task 12: Pattern detector agent

**Files:**
- Create: `agents/pattern_detector.py`
- Test: `tests/test_pattern_detector.py`

**Interfaces:**
- Consumes: `agents.specialist_factory.make_specialist_node`, `tools.llm_tools.{account_history, similar_fraud_cases}`.
- Produces: `pattern_detector_node: Callable[[TransactionState], dict]` writing to `pattern_findings`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pattern_detector.py
from unittest.mock import MagicMock

from agents.pattern_detector import pattern_detector_node
from state import new_state


def test_pattern_detector_node_uses_expected_tools_and_state_key(monkeypatch):
    captured = {}

    def fake_create_react_agent(llm, tools, prompt):
        captured["tools"] = tools
        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"messages": [MagicMock(content="matches known pattern")]}
        return fake_agent

    monkeypatch.setattr("agents.specialist_factory.ChatOpenAI", lambda **kwargs: object())
    monkeypatch.setattr("agents.specialist_factory.create_react_agent", fake_create_react_agent)

    state = new_state({"transaction_id": "txn_1"})
    result = pattern_detector_node(state)

    assert result["pattern_findings"] == "matches known pattern"
    assert [t.name for t in captured["tools"]] == ["account_history", "similar_fraud_cases"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pattern_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.pattern_detector'`

- [ ] **Step 3: Write `agents/pattern_detector.py`**

```python
from agents.specialist_factory import make_specialist_node
from tools.llm_tools import account_history, similar_fraud_cases

SYSTEM_PROMPT = (
    "You are a fraud pattern detection specialist. Use the account history "
    "tool to understand the account's normal behavior and the similar fraud "
    "cases tool to check whether this transaction resembles any known fraud "
    "pattern. Summarize in 2-3 sentences whether this transaction matches "
    "known fraud patterns."
)

pattern_detector_node = make_specialist_node(
    name="pattern_detector",
    state_key="pattern_findings",
    tools=[account_history, similar_fraud_cases],
    system_prompt=SYSTEM_PROMPT,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pattern_detector.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add agents/pattern_detector.py tests/test_pattern_detector.py
git commit -m "feat: add pattern detector specialist agent"
```

---

## Task 13: Aggregator agent and post-aggregation routing

**Files:**
- Create: `agents/aggregator.py`
- Test: `tests/test_aggregator.py`

**Interfaces:**
- Consumes: `state.TransactionState`, `langchain_openai.ChatOpenAI`, `pydantic.BaseModel`.
- Produces: `AggregatorOutput` (pydantic model, fields `composite_score: float`, `reasoning: str`); `aggregator_node(state) -> dict` (sets `composite_score`, `aggregate_reasoning`, appends `audit_log`); `route_after_aggregator(state) -> Literal["human_review", "resolution"]` using `AGGREGATOR_THRESHOLD = 0.5`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_aggregator.py
from agents.aggregator import AggregatorOutput, aggregator_node, route_after_aggregator
from state import new_state


class _FakeLLM:
    def __init__(self, output):
        self._output = output
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt
        return self._output


def test_aggregator_node_returns_composite_score_and_reasoning(monkeypatch):
    fake_output = AggregatorOutput(composite_score=0.72, reasoning="Multiple risk signals align.")
    monkeypatch.setattr("agents.aggregator._build_llm", lambda: _FakeLLM(fake_output))

    state = new_state({"transaction_id": "txn_1"})
    state["triage_score"] = 0.6
    state["analyst_findings"] = "unusual amount"
    state["identity_findings"] = "new device"
    state["pattern_findings"] = "matches known fraud pattern"

    result = aggregator_node(state)

    assert result["composite_score"] == 0.72
    assert result["aggregate_reasoning"] == "Multiple risk signals align."
    assert result["audit_log"][-1].startswith("aggregator: composite_score=0.72")


def test_route_after_aggregator_at_threshold_goes_to_human_review():
    state = new_state({"transaction_id": "txn_1"})
    state["composite_score"] = 0.5
    assert route_after_aggregator(state) == "human_review"


def test_route_after_aggregator_below_threshold_goes_to_resolution():
    state = new_state({"transaction_id": "txn_1"})
    state["composite_score"] = 0.49
    assert route_after_aggregator(state) == "resolution"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aggregator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.aggregator'`

- [ ] **Step 3: Write `agents/aggregator.py`**

```python
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from state import TransactionState

AGGREGATOR_THRESHOLD = 0.5
DEFAULT_MODEL = "gpt-4o-mini"


class AggregatorOutput(BaseModel):
    composite_score: float = Field(description="Overall fraud risk score from 0.0 (safe) to 1.0 (certain fraud)")
    reasoning: str = Field(description="2-4 sentence plain-English explanation combining all specialist findings")


def _build_llm(model: str = DEFAULT_MODEL):
    return ChatOpenAI(model=model, temperature=0).with_structured_output(AggregatorOutput)


def aggregator_node(state: TransactionState) -> dict:
    llm = _build_llm()
    prompt = (
        "Combine the following fraud investigation findings into a single "
        f"composite risk score and rationale.\n\nTriage score: {state['triage_score']:.2f}\n"
        f"Transaction analyst: {state['analyst_findings']}\n"
        f"Identity verifier: {state['identity_findings']}\n"
        f"Pattern detector: {state['pattern_findings']}\n"
    )
    result: AggregatorOutput = llm.invoke(prompt)
    return {
        "composite_score": result.composite_score,
        "aggregate_reasoning": result.reasoning,
        "audit_log": state["audit_log"]
        + [f"aggregator: composite_score={result.composite_score:.2f} — {result.reasoning}"],
    }


def route_after_aggregator(state: TransactionState) -> Literal["human_review", "resolution"]:
    if state["composite_score"] is not None and state["composite_score"] >= AGGREGATOR_THRESHOLD:
        return "human_review"
    return "resolution"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_aggregator.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add agents/aggregator.py tests/test_aggregator.py
git commit -m "feat: add aggregator agent with structured output and post-aggregation routing"
```

---

## Task 14: Human review node

**Files:**
- Create: `agents/human_review.py`
- Test: `tests/test_human_review.py`

**Interfaces:**
- Consumes: `state.TransactionState`.
- Produces: `human_review_node(state) -> dict` appending an `audit_log` entry (this node is configured with `interrupt_before` in the graph, not here).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_human_review.py
from agents.human_review import human_review_node
from state import new_state


def test_human_review_node_appends_audit_log_with_composite_score():
    state = new_state({"transaction_id": "txn_1"})
    state["composite_score"] = 0.72

    result = human_review_node(state)

    assert result["audit_log"] == [
        "human_review: awaiting reviewer decision (composite_score=0.72)"
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_human_review.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.human_review'`

- [ ] **Step 3: Write `agents/human_review.py`**

```python
from state import TransactionState


def human_review_node(state: TransactionState) -> dict:
    return {
        "audit_log": state["audit_log"]
        + [f"human_review: awaiting reviewer decision (composite_score={state['composite_score']:.2f})"]
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_human_review.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add agents/human_review.py tests/test_human_review.py
git commit -m "feat: add human review node"
```

---

## Task 15: Resolution node

**Files:**
- Create: `agents/resolution.py`
- Test: `tests/test_resolution.py`

**Interfaces:**
- Consumes: `state.TransactionState`.
- Produces: `resolution_node(state) -> dict` setting `final_decision` to `"approved"`, `"declined"`, or `"escalated"` and appending `audit_log`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolution.py
from agents.resolution import resolution_node
from state import new_state


def test_auto_approve_resolves_to_approved():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "auto_approve"

    result = resolution_node(state)

    assert result["final_decision"] == "approved"


def test_auto_decline_resolves_to_declined():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "auto_decline"

    result = resolution_node(state)

    assert result["final_decision"] == "declined"


def test_investigate_with_human_approve_resolves_to_approved():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "investigate"
    state["human_decision"] = "approve"

    result = resolution_node(state)

    assert result["final_decision"] == "approved"


def test_investigate_with_human_decline_resolves_to_declined():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "investigate"
    state["human_decision"] = "decline"

    result = resolution_node(state)

    assert result["final_decision"] == "declined"


def test_investigate_with_human_escalate_resolves_to_escalated():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "investigate"
    state["human_decision"] = "escalate"

    result = resolution_node(state)

    assert result["final_decision"] == "escalated"


def test_investigate_with_no_human_decision_fails_safe_to_declined():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "investigate"

    result = resolution_node(state)

    assert result["final_decision"] == "declined"


def test_resolution_node_appends_audit_log():
    state = new_state({"transaction_id": "txn_1"})
    state["triage_decision"] = "auto_approve"

    result = resolution_node(state)

    assert result["audit_log"] == ["resolution: final_decision=approved"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resolution.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.resolution'`

- [ ] **Step 3: Write `agents/resolution.py`**

```python
from state import TransactionState


def resolution_node(state: TransactionState) -> dict:
    if state["triage_decision"] == "auto_approve":
        final = "approved"
    elif state["triage_decision"] == "auto_decline":
        final = "declined"
    elif state["human_decision"] == "approve":
        final = "approved"
    elif state["human_decision"] == "decline":
        final = "declined"
    elif state["human_decision"] == "escalate":
        final = "escalated"
    else:
        final = "declined"

    return {
        "final_decision": final,
        "audit_log": state["audit_log"] + [f"resolution: final_decision={final}"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resolution.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add agents/resolution.py tests/test_resolution.py
git commit -m "feat: add resolution node"
```

---

## Task 16: Graph wiring and LangGraph Studio config

**Files:**
- Create: `graph.py`
- Create: `langgraph.json`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: all node functions from Tasks 7–15, `langgraph.graph.{StateGraph, START, END}`, `langgraph.checkpoint.sqlite.SqliteSaver`.
- Produces: `build_graph(nodes: dict[str, Callable], checkpointer) -> CompiledGraph`; module-level `graph` (compiled with the real `DEFAULT_NODES` and a disk-backed `SqliteSaver`), interrupting before `human_review`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_graph.py
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from graph import build_graph
from state import new_state


def _stub_node(name, **extra_fields):
    def node(state):
        return {"audit_log": state["audit_log"] + [name], **extra_fields}

    return node


def _make_test_graph(triage_decision="investigate"):
    def triage_stub(state):
        score = {"auto_decline": 0.9, "auto_approve": 0.1, "investigate": 0.4}[triage_decision]
        return {
            "triage_score": score,
            "triage_decision": triage_decision,
            "audit_log": state["audit_log"] + ["triage"],
        }

    nodes = {
        "ingest": _stub_node("ingest"),
        "triage": triage_stub,
        "auto_approve": _stub_node("auto_approve"),
        "auto_decline": _stub_node("auto_decline"),
        "transaction_analyst": _stub_node("transaction_analyst", analyst_findings="a"),
        "identity_verifier": _stub_node("identity_verifier", identity_findings="i"),
        "pattern_detector": _stub_node("pattern_detector", pattern_findings="p"),
        "aggregator": lambda state: {
            "composite_score": 0.8,
            "aggregate_reasoning": "risky",
            "audit_log": state["audit_log"] + ["aggregator"],
        },
        "human_review": _stub_node("human_review"),
        "resolution": lambda state: {
            "final_decision": "escalated",
            "audit_log": state["audit_log"] + ["resolution"],
        },
    }
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return build_graph(nodes, checkpointer=SqliteSaver(conn))


def test_investigate_path_pauses_before_human_review():
    test_graph = _make_test_graph("investigate")
    config = {"configurable": {"thread_id": "test-1"}}

    test_graph.invoke(new_state({"transaction_id": "txn_x"}), config)

    assert test_graph.get_state(config).next == ("human_review",)


def test_resume_after_human_review_reaches_resolution():
    test_graph = _make_test_graph("investigate")
    config = {"configurable": {"thread_id": "test-2"}}
    test_graph.invoke(new_state({"transaction_id": "txn_y"}), config)

    test_graph.update_state(config, {"human_decision": "escalate"})
    result = test_graph.invoke(None, config)

    assert result["final_decision"] == "escalated"
    assert "resolution" in result["audit_log"]
    assert test_graph.get_state(config).next == ()


def test_auto_approve_path_skips_investigation_and_review():
    test_graph = _make_test_graph("auto_approve")
    config = {"configurable": {"thread_id": "test-3"}}

    result = test_graph.invoke(new_state({"transaction_id": "txn_z"}), config)

    assert result["audit_log"] == ["ingest", "triage", "auto_approve", "resolution"]
    assert test_graph.get_state(config).next == ()


def test_auto_decline_path_skips_investigation_and_review():
    test_graph = _make_test_graph("auto_decline")
    config = {"configurable": {"thread_id": "test-4"}}

    result = test_graph.invoke(new_state({"transaction_id": "txn_w"}), config)

    assert result["audit_log"] == ["ingest", "triage", "auto_decline", "resolution"]
    assert test_graph.get_state(config).next == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_graph.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'graph'`

- [ ] **Step 3: Write `graph.py`**

```python
import os
import sqlite3
from typing import Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agents.aggregator import aggregator_node, route_after_aggregator
from agents.human_review import human_review_node
from agents.identity_verifier import identity_verifier_node
from agents.ingest import ingest_node
from agents.pattern_detector import pattern_detector_node
from agents.resolution import resolution_node
from agents.transaction_analyst import transaction_analyst_node
from agents.triage import auto_approve_node, auto_decline_node, route_after_triage, triage_node
from state import TransactionState

NodeMap = dict[str, Callable]

NODE_NAMES = [
    "ingest",
    "triage",
    "auto_approve",
    "auto_decline",
    "transaction_analyst",
    "identity_verifier",
    "pattern_detector",
    "aggregator",
    "human_review",
    "resolution",
]


def build_graph(nodes: NodeMap, checkpointer=None):
    builder = StateGraph(TransactionState)

    for name in NODE_NAMES:
        builder.add_node(name, nodes[name])

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "triage")
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "auto_approve": "auto_approve",
            "auto_decline": "auto_decline",
            "transaction_analyst": "transaction_analyst",
            "identity_verifier": "identity_verifier",
            "pattern_detector": "pattern_detector",
        },
    )
    builder.add_edge("auto_approve", "resolution")
    builder.add_edge("auto_decline", "resolution")
    builder.add_edge("transaction_analyst", "aggregator")
    builder.add_edge("identity_verifier", "aggregator")
    builder.add_edge("pattern_detector", "aggregator")
    builder.add_conditional_edges(
        "aggregator",
        route_after_aggregator,
        {"human_review": "human_review", "resolution": "resolution"},
    )
    builder.add_edge("human_review", "resolution")
    builder.add_edge("resolution", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["human_review"])


DEFAULT_NODES: NodeMap = {
    "ingest": ingest_node,
    "triage": triage_node,
    "auto_approve": auto_approve_node,
    "auto_decline": auto_decline_node,
    "transaction_analyst": transaction_analyst_node,
    "identity_verifier": identity_verifier_node,
    "pattern_detector": pattern_detector_node,
    "aggregator": aggregator_node,
    "human_review": human_review_node,
    "resolution": resolution_node,
}

_checkpoint_path = os.environ.get("CHECKPOINT_DB_PATH", "checkpoints.sqlite")
# check_same_thread=False: Streamlit and langgraph dev may access the
# connection from a different thread than the one that created it.
_conn = sqlite3.connect(_checkpoint_path, check_same_thread=False)
checkpointer = SqliteSaver(_conn)
graph = build_graph(DEFAULT_NODES, checkpointer=checkpointer)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_graph.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write `langgraph.json`**

```json
{
  "dependencies": ["."],
  "graphs": {
    "fraud_guard": "./graph.py:graph"
  },
  "env": ".env"
}
```

- [ ] **Step 6: Commit**

```bash
git add graph.py langgraph.json tests/test_graph.py
git commit -m "feat: wire tiered escalation StateGraph with SqliteSaver checkpointing"
```

---

## Task 17: UI logic (graph-driving functions)

**Files:**
- Create: `ui/logic.py`
- Test: `tests/test_ui_logic.py`

**Interfaces:**
- Consumes: `data.synthetic_transactions.{SCENARIOS, get_scenario}`, `state.new_state`, a compiled graph object (dependency-injected, not imported directly — keeps this module testable without touching the real `graph.py` singleton's LLM nodes).
- Produces: `start_transaction(graph, scenario_name: str) -> str` (returns `thread_id`); `resume_transaction(graph, thread_id: str, decision: str) -> dict` (returns final state after resuming); `get_pending_reviews(graph) -> list[dict]` (returns state snapshots currently paused at `human_review`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_logic.py
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from graph import build_graph
from ui.logic import get_pending_reviews, resume_transaction, start_transaction


def _stub_node(name, **extra_fields):
    def node(state):
        return {"audit_log": state["audit_log"] + [name], **extra_fields}

    return node


def _make_investigate_test_graph():
    nodes = {
        "ingest": _stub_node("ingest"),
        "triage": lambda state: {
            "triage_score": 0.4,
            "triage_decision": "investigate",
            "audit_log": state["audit_log"] + ["triage"],
        },
        "auto_approve": _stub_node("auto_approve"),
        "auto_decline": _stub_node("auto_decline"),
        "transaction_analyst": _stub_node("transaction_analyst", analyst_findings="a"),
        "identity_verifier": _stub_node("identity_verifier", identity_findings="i"),
        "pattern_detector": _stub_node("pattern_detector", pattern_findings="p"),
        "aggregator": lambda state: {
            "composite_score": 0.9,
            "aggregate_reasoning": "risky",
            "audit_log": state["audit_log"] + ["aggregator"],
        },
        "human_review": _stub_node("human_review"),
        "resolution": lambda state: {
            "final_decision": "escalated",
            "audit_log": state["audit_log"] + ["resolution"],
        },
    }
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return build_graph(nodes, checkpointer=SqliteSaver(conn))


def test_start_transaction_then_appears_in_pending_reviews():
    test_graph = _make_investigate_test_graph()

    thread_id = start_transaction(test_graph, "borderline_wire")
    pending = get_pending_reviews(test_graph)

    assert thread_id == "txn_003"
    assert any(case["thread_id"] == "txn_003" for case in pending)


def test_resume_transaction_clears_pending_review():
    test_graph = _make_investigate_test_graph()
    thread_id = start_transaction(test_graph, "borderline_wire")

    result = resume_transaction(test_graph, thread_id, "approve")

    assert result["final_decision"] == "escalated"
    pending = get_pending_reviews(test_graph)
    assert not any(case["thread_id"] == thread_id for case in pending)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_logic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.logic'`

- [ ] **Step 3: Write `ui/logic.py`**

```python
from typing import Any

from data.synthetic_transactions import SCENARIOS, get_scenario
from state import new_state


def start_transaction(graph: Any, scenario_name: str) -> str:
    transaction = get_scenario(scenario_name)
    thread_id = transaction["transaction_id"]
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(new_state(transaction), config)
    return thread_id


def resume_transaction(graph: Any, thread_id: str, decision: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"human_decision": decision})
    return graph.invoke(None, config)


def get_pending_reviews(graph: Any) -> list[dict]:
    pending = []
    for transaction in SCENARIOS.values():
        thread_id = transaction["transaction_id"]
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(config)
        if snapshot.values and snapshot.next == ("human_review",):
            pending.append({"thread_id": thread_id, **snapshot.values})
    return pending
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_logic.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/logic.py tests/test_ui_logic.py
git commit -m "feat: add testable UI logic for driving the graph from a queue"
```

---

## Task 18: Streamlit review UI

**Files:**
- Create: `ui/app.py`
- Test: `tests/test_ui_app.py`

**Interfaces:**
- Consumes: `graph.graph`, `data.synthetic_transactions.SCENARIOS`, `ui.logic.{start_transaction, resume_transaction, get_pending_reviews}`.
- Produces: a runnable Streamlit page (`streamlit run ui/app.py`) with a scenario picker, a pending-review queue with Approve/Decline/Escalate buttons, and a live audit-log view.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_app.py
from streamlit.testing.v1 import AppTest


def test_app_renders_without_error():
    at = AppTest.from_file("ui/app.py")
    at.run()

    assert not at.exception
    assert at.title[0].value == "Fraud Guard — Live Transaction Review"


def test_app_shows_scenario_selectbox():
    at = AppTest.from_file("ui/app.py")
    at.run()

    assert len(at.selectbox) == 1
    assert set(at.selectbox[0].options) == {
        "clean_coffee",
        "impossible_travel",
        "borderline_wire",
        "borderline_restart_demo",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_app.py -v`
Expected: FAIL with `FileNotFoundError` or `ModuleNotFoundError` (no `ui/app.py` yet)

- [ ] **Step 3: Write `ui/app.py`**

```python
import streamlit as st

from data.synthetic_transactions import SCENARIOS
from graph import graph
from ui.logic import get_pending_reviews, resume_transaction, start_transaction

st.set_page_config(page_title="Fraud Guard", layout="wide")
st.title("Fraud Guard — Live Transaction Review")

st.header("Run a scenario")
scenario_choice = st.selectbox("Scenario", list(SCENARIOS.keys()))
if st.button("Submit transaction"):
    thread_id = start_transaction(graph, scenario_choice)
    st.success(f"Submitted {thread_id}")

st.header("Pending human review")
for case in get_pending_reviews(graph):
    with st.container(border=True):
        st.subheader(case["thread_id"])
        st.write(f"Composite score: {case['composite_score']:.2f}")
        st.write(case["aggregate_reasoning"])
        cols = st.columns(3)
        if cols[0].button("Approve", key=f"approve_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "approve")
            st.rerun()
        if cols[1].button("Decline", key=f"decline_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "decline")
            st.rerun()
        if cols[2].button("Escalate", key=f"escalate_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "escalate")
            st.rerun()
        st.write("Audit log:")
        for line in case["audit_log"]:
            st.text(line)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_app.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Manually verify the live UI**

```bash
streamlit run ui/app.py
```

In the browser: select `borderline_wire`, click **Submit transaction**, confirm a pending-review card appears with a composite score and rationale, click **Approve**, confirm the card disappears.

- [ ] **Step 6: Commit**

```bash
git add ui/app.py tests/test_ui_app.py
git commit -m "feat: add Streamlit review UI"
```

---

## Task 19: README with setup and demo script

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: setup instructions and the talk demo script for a new contributor/presenter with zero prior context.

- [ ] **Step 1: Write `README.md`**

```markdown
# Fraud Guard — LangGraph Fintech Demo

A LangGraph demo built for a conference talk: a tiered fraud-detection
pipeline that only pays for expensive multi-agent LLM investigation on
borderline transactions, pauses for human review when risk stays high, and
survives a process restart mid-review thanks to checkpointing.

## Setup

\`\`\`bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in OPENAI_API_KEY
\`\`\`

## Run the tests

\`\`\`bash
pytest
\`\`\`

All tests run offline — no `OPENAI_API_KEY` required.

## Run LangGraph Studio

\`\`\`bash
langgraph dev
\`\`\`

Opens a local Studio UI rendering the `fraud_guard` graph. Requires
`OPENAI_API_KEY` in `.env` to actually execute specialist/aggregator nodes.

## Run the review UI

\`\`\`bash
streamlit run ui/app.py
\`\`\`

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

## Project structure

See `docs/superpowers/specs/2026-07-11-langgraph-fraud-demo-design.md` for
the full design.
\`\`\`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add setup instructions and demo script"
```

---

## Final verification

- [ ] **Run the full test suite**

```bash
pytest -v
```

Expected: all tests across Tasks 2–18 pass (approximately 45 tests), no
network calls, no `OPENAI_API_KEY` required.

- [ ] **Manually run the demo script from Task 19 end-to-end** with a real
  `OPENAI_API_KEY` set, using both `langgraph dev` and `streamlit run ui/app.py`,
  confirming all four scenarios behave as described in the design spec.
