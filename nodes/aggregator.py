from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from core import audit
from core.state import TransactionState

AGGREGATOR_THRESHOLD = 0.5
DEFAULT_MODEL = "gpt-4o-mini"


class AggregatorOutput(BaseModel):
    composite_score: float = Field(description="Overall fraud risk score from 0.0 (safe) to 1.0 (certain fraud)")
    reasoning: str = Field(description="2-4 sentence plain-English explanation combining all specialist findings")


def _build_llm(model: str = DEFAULT_MODEL):
    return ChatOpenAI(model=model, temperature=0).with_structured_output(AggregatorOutput)


def aggregator_node(state: TransactionState) -> dict:
    llm = _build_llm()
    prompt = (
        "Combine the following fraud investigation findings into a single "
        f"composite risk score and rationale.\n\nTriage score: {state['triage_score']:.2f}\n"
        f"Transaction analyst: {state['analyst_findings']}\n"
        f"Identity verifier: {state['identity_findings']}\n"
        f"Pattern detector: {state['pattern_findings']}\n"
    )
    result: AggregatorOutput = llm.invoke(prompt)
    return {
        "composite_score": result.composite_score,
        "aggregate_reasoning": result.reasoning,
        "audit_log": [audit.summary("aggregator", result.reasoning, score=result.composite_score)],
    }


def route_after_aggregator(state: TransactionState) -> Literal["human_review", "resolution"]:
    if state["composite_score"] is not None and state["composite_score"] >= AGGREGATOR_THRESHOLD:
        return "human_review"
    return "resolution"
