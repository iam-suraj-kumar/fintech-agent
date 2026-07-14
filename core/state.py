import operator
from typing import Annotated, Literal, TypedDict


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
    audit_log: Annotated[list[dict], operator.add]


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
