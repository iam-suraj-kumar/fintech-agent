import asyncio
import json
import os
import sys

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

_SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_server", "geolocation_server.py"
)

_mcp_tools_cache: list | None = None


async def _load_mcp_tools():
    client = MultiServerMCPClient(
        {
            "geolocation": {
                "command": sys.executable,
                "args": [_SERVER_SCRIPT],
                "transport": "stdio",
            }
        }
    )
    return await client.get_tools()


def _get_raw_mcp_tool():
    global _mcp_tools_cache
    if _mcp_tools_cache is None:
        _mcp_tools_cache = asyncio.run(_load_mcp_tools())
    return next(t for t in _mcp_tools_cache if t.name == "geolocation")


def get_geolocation_tool():
    # The MCP-loaded tool only implements an async run method; the specialist
    # agents are invoked synchronously, so this wraps it in a plain sync tool.
    mcp_tool = _get_raw_mcp_tool()

    @tool
    def geolocation(ip: str) -> dict:
        """Look up the real country, region, city, and ISP for a public IP address via the live MCP geolocation server."""
        content = asyncio.run(mcp_tool.ainvoke({"ip": ip}))
        # langchain-mcp-adapters returns MCP content blocks, not a plain dict:
        # unwrap the JSON text payload the FastMCP tool actually returned.
        return json.loads(content[0]["text"])

    return geolocation
