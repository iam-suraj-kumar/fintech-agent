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
