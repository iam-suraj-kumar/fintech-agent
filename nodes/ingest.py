from core import audit
from core.state import TransactionState


def ingest_node(state: TransactionState) -> dict:
    txn_id = state["transaction"].get("transaction_id", "unknown")
    return {"audit_log": [audit.info("ingest", f"received transaction {txn_id}")]}
