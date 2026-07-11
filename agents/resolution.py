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
        "audit_log": [f"resolution: final_decision={final}"],
    }
