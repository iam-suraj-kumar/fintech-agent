from typing import Callable

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from state import TransactionState

DEFAULT_MODEL = "gpt-4o-mini"


def make_specialist_node(
    name: str,
    state_key: str,
    tools: list,
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> Callable[[TransactionState], dict]:
    agent_holder: dict = {}

    def _get_agent():
        if "agent" not in agent_holder:
            llm = ChatOpenAI(model=model, temperature=0)
            agent_holder["agent"] = create_react_agent(llm, tools, prompt=system_prompt)
        return agent_holder["agent"]

    def node(state: TransactionState) -> dict:
        agent = _get_agent()
        transaction = state["transaction"]
        result = agent.invoke(
            {"messages": [("user", f"Investigate this transaction: {transaction}")]}
        )
        finding = result["messages"][-1].content
        return {
            state_key: finding,
            "audit_log": [f"{name}: {finding}"],
        }

    return node
