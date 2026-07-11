import os
import sqlite3
from typing import Callable

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.sqlite import SqliteStore

load_dotenv()

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


def build_graph(nodes: NodeMap, checkpointer=None, store=None):
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

    return builder.compile(checkpointer=checkpointer, store=store, interrupt_before=["human_review"])


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
_memory_path = os.environ.get("MEMORY_DB_PATH", "account_memory.sqlite")
# check_same_thread=False: Streamlit and langgraph dev may access the
# connection from a different thread than the one that created it.
_conn = sqlite3.connect(_checkpoint_path, check_same_thread=False)
checkpointer = SqliteSaver(_conn)

_memory_conn = sqlite3.connect(_memory_path, check_same_thread=False, isolation_level=None)
store = SqliteStore(_memory_conn)
store.setup()

graph = build_graph(DEFAULT_NODES, checkpointer=checkpointer, store=store)
