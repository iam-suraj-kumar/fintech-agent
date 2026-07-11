from agents.specialist_factory import make_specialist_node
from tools.llm_tools import device_fingerprint, geolocation

SYSTEM_PROMPT = (
    "You are an identity and device verification specialist. Use the device "
    "fingerprint and geolocation tools to assess whether the device and "
    "location used for this transaction are consistent with legitimate "
    "account activity. Summarize your assessment in 2-3 sentences."
)

identity_verifier_node = make_specialist_node(
    name="identity_verifier",
    state_key="identity_findings",
    tools=[device_fingerprint, geolocation],
    system_prompt=SYSTEM_PROMPT,
)
