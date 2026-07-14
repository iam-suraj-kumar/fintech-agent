from core import audit
from core.state import TransactionState


def human_review_node(state: TransactionState) -> dict:
    return {
        "audit_log": [
            audit.info(
                "human_review",
                f"awaiting reviewer decision (composite_score={state['composite_score']:.2f})",
            )
        ]
    }
