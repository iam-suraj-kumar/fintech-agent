import uuid
from typing import Any

from data.synthetic_transactions import get_scenario
from state import new_state


def start_transaction(graph: Any, transaction_id_input: str) -> str:
    transaction = get_scenario(transaction_id_input)
    # A fresh, unique thread_id per submission — reusing the scenario's fixed
    # transaction_id as the thread_id would append this run's audit_log onto
    # any earlier run's history on that same thread (audit_log's reducer is
    # additive), corrupting the trace on every resubmit.
    thread_id = f"{transaction['transaction_id']}-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(new_state(transaction), config)
    return thread_id


def resume_transaction(graph: Any, thread_id: str, decision: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"human_decision": decision})
    return graph.invoke(None, config)


def _all_thread_ids(graph: Any) -> set[str]:
    return {
        checkpoint_tuple.config["configurable"]["thread_id"]
        for checkpoint_tuple in graph.checkpointer.list(None)
    }


def get_pending_reviews(graph: Any) -> list[dict]:
    pending = []
    for thread_id in _all_thread_ids(graph):
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(config)
        if snapshot.values and snapshot.next == ("human_review",):
            pending.append({"thread_id": thread_id, **snapshot.values})
    return pending


def get_decision_history(graph: Any) -> list[dict]:
    history = []
    for thread_id in _all_thread_ids(graph):
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(config)
        if snapshot.values and snapshot.next == () and snapshot.values.get("final_decision"):
            history.append({"thread_id": thread_id, **snapshot.values})
    return history
