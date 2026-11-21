from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core.specialist_factory import _format_trace

# Gemini returns message content as a list of blocks; OpenAI returns a string.
GEMINI_CONTENT = [{"type": "text", "text": "High risk: "}, {"type": "text", "text": "sanctions match."}]


def _messages(final_content):
    return [
        HumanMessage("Investigate this transaction"),
        AIMessage("", tool_calls=[{"name": "sanctions_check", "args": {"beneficiary_name": "X"}, "id": "c1"}]),
        ToolMessage('{"on_list": true}', name="sanctions_check", tool_call_id="c1"),
        AIMessage(final_content),
    ]


def test_summary_is_plain_text_for_gemini_block_content():
    summary = _format_trace("transaction_analyst", _messages(GEMINI_CONTENT))[-1]
    assert summary["kind"] == "summary"
    assert summary["text"] == "High risk: sanctions match."


def test_summary_is_unchanged_for_string_content():
    summary = _format_trace("transaction_analyst", _messages("High risk."))[-1]
    assert summary["text"] == "High risk."


def test_trace_kinds():
    kinds = [e["kind"] for e in _format_trace("transaction_analyst", _messages("ok"))]
    assert kinds == ["tool_call", "tool_result", "summary"]


def test_summary_is_exactly_str():
    # A str subclass could fail to serialize in the SQLite checkpointer.
    summary = _format_trace("transaction_analyst", _messages(GEMINI_CONTENT))[-1]
    assert type(summary["text"]) is str
