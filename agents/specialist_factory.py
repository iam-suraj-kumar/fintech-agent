import json
from typing import Callable

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

import audit
from state import TransactionState

DEFAULT_MODEL = "gpt-4o-mini"


def _parse_tool_content(content):
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return content


def _format_trace(name: str, messages: list) -> list[dict]:
    entries = []
    for message in messages[1:]:  # skip the initial human prompt we sent
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                entries.append(audit.tool_call(name, call["name"], call["args"]))
        elif isinstance(message, ToolMessage):
            entries.append(audit.tool_result(name, message.name, _parse_tool_content(message.content)))
        elif isinstance(message, AIMessage) and message.content:
            entries.append(audit.summary(name, message.content))
    return entries


def make_specialist_node(
    name: str,
    state_key: str,
    tools: list | Callable[[], list],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> Callable[[TransactionState], dict]:
    agent_holder: dict = {}

    def _get_agent():
        if "agent" not in agent_holder:
            resolved_tools = tools() if callable(tools) else tools
            llm = ChatOpenAI(model=model, temperature=0)
            agent_holder["agent"] = create_react_agent(llm, resolved_tools, prompt=system_prompt)
        return agent_holder["agent"]

    def node(state: TransactionState) -> dict:
        agent = _get_agent()
        transaction = state["transaction"]
        result = agent.invoke(
            {"messages": [("user", f"Investigate this transaction: {transaction}")]}
        )
        messages = result["messages"]
        finding = messages[-1].content
        return {
            state_key: finding,
            "audit_log": _format_trace(name, messages),
        }

    return node
