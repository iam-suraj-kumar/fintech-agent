from state import TransactionState


def human_review_node(state: TransactionState) -> dict:
    return {
        "audit_log": [
            f"human_review: awaiting reviewer decision (composite_score={state['composite_score']:.2f})"
        ]
    }
