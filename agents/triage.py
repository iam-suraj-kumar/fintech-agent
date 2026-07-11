from langgraph.config import get_store

import audit
from state import TransactionState
from tools.mock_apis import (
    get_account_history,
    get_device_fingerprint,
    get_geolocation,
    get_merchant_risk_score,
)

AUTO_DECLINE_THRESHOLD = 0.65
INVESTIGATE_THRESHOLD = 0.30
MEMORY_NAMESPACE_PREFIX = "account_memory"


def _account_memory_penalty(account_id: str) -> float:
    # get_store() only works inside a graph compiled with store=...; direct
    # unit-style calls to triage_node/_compute_triage_score without a
    # compiled graph context fall back to no penalty rather than erroring.
    try:
        store = get_store()
    except RuntimeError:
        return 0.0

    past_decisions = store.search((MEMORY_NAMESPACE_PREFIX, account_id))
    escalations = sum(1 for item in past_decisions if item.value.get("final_decision") == "escalated")
    declines = sum(1 for item in past_decisions if item.value.get("final_decision") == "declined")
    return min(0.15 * escalations + 0.10 * declines, 0.3)


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

    score += _account_memory_penalty(transaction["account_id"])

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
        "audit_log": [audit.info("triage", f"score={score:.2f} decision={decision}")],
    }


def route_after_triage(state: TransactionState) -> list[str]:
    decision = state["triage_decision"]
    if decision == "investigate":
        return ["transaction_analyst", "identity_verifier", "pattern_detector"]
    return [decision]


def auto_approve_node(state: TransactionState) -> dict:
    return {"audit_log": [audit.info("auto_approve", "triage score below investigation threshold")]}


def auto_decline_node(state: TransactionState) -> dict:
    return {"audit_log": [audit.info("auto_decline", "triage score indicates high-confidence fraud")]}
