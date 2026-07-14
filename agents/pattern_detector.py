from core.specialist_factory import make_specialist_node
from tools.llm_tools import account_history, similar_fraud_cases

SYSTEM_PROMPT = (
    "You are a fraud pattern detection specialist. Use the account history "
    "tool to understand the account's normal behavior and the similar fraud "
    "cases tool to check whether this transaction resembles any known fraud "
    "pattern. Summarize in 2-3 sentences whether this transaction matches "
    "known fraud patterns."
)

pattern_detector_node = make_specialist_node(
    name="pattern_detector",
    state_key="pattern_findings",
    tools=[account_history, similar_fraud_cases],
    system_prompt=SYSTEM_PROMPT,
)
