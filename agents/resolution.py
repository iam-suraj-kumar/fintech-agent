import uuid

from langgraph.config import get_store

import audit
from state import TransactionState

MEMORY_NAMESPACE_PREFIX = "account_memory"


def _remember_decision(account_id: str, transaction_id: str, final_decision: str, composite_score: float | None) -> None:
    try:
        store = get_store()
    except RuntimeError:
        return

    store.put(
        (MEMORY_NAMESPACE_PREFIX, account_id),
        key=f"{transaction_id}-{uuid.uuid4().hex[:6]}",
        value={"final_decision": final_decision, "composite_score": composite_score},
    )


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

    transaction = state["transaction"]
    _remember_decision(transaction["account_id"], transaction["transaction_id"], final, state["composite_score"])

    return {
        "final_decision": final,
        "audit_log": [audit.decision("resolution", f"final_decision={final}")],
    }
