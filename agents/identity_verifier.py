from core.specialist_factory import make_specialist_node
from tools.llm_tools import device_fingerprint
from tools.mcp_geolocation import get_geolocation_tool

SYSTEM_PROMPT = (
    "You are an identity and device verification specialist. Use the device "
    "fingerprint tool and the geolocation tool to assess whether the device "
    "and location used for this transaction are consistent with legitimate "
    "account activity. The transaction's `real_ip` field is a genuine public "
    "IP address — pass that value to the geolocation tool, not the symbolic "
    "`ip` field, which is an internal bookkeeping key only. Summarize your "
    "assessment in 2-3 sentences."
)

identity_verifier_node = make_specialist_node(
    name="identity_verifier",
    state_key="identity_findings",
    tools=lambda: [device_fingerprint, get_geolocation_tool()],
    system_prompt=SYSTEM_PROMPT,
)
