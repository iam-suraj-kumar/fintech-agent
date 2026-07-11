from agents.specialist_factory import make_specialist_node
from tools.llm_tools import account_history, merchant_risk_score

SYSTEM_PROMPT = (
    "You are a transaction analyst investigating a potentially fraudulent "
    "financial transaction. Use the account history and merchant risk tools "
    "to check whether the amount and merchant are consistent with the "
    "account's typical behavior. Summarize your assessment in 2-3 sentences."
)

transaction_analyst_node = make_specialist_node(
    name="transaction_analyst",
    state_key="analyst_findings",
    tools=[account_history, merchant_risk_score],
    system_prompt=SYSTEM_PROMPT,
)
