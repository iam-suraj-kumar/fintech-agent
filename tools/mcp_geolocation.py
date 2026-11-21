import asyncio
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

_SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_server", "geolocation_server.py"
)

_mcp_tools_cache: list | None = None


def _run_sync(coro):
    """Run a coroutine to completion from sync code, even inside Jupyter.

    asyncio.run() refuses to start when an event loop is already running (Jupyter
    always has one), so in that case the coroutine runs on its own loop in a worker thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _ensure_server_stderr_has_fileno() -> None:
    """Make sure the MCP server subprocess gets a stderr it can use.

    The MCP client passes the server the sys.stderr that existed when `mcp` was imported.
    In Google Colab that is a notebook stream with no file descriptor, so starting the
    server fails with "UnsupportedOperation: fileno". Use the process's real stderr then.
    """
    import mcp.client.stdio as stdio

    start_server = stdio.stdio_client.__wrapped__
    (errlog,) = start_server.__defaults__
    try:
        errlog.fileno()
    except (AttributeError, OSError, ValueError):  # io.UnsupportedOperation is both
        real = sys.__stderr__
        try:
            real.fileno()
        except (AttributeError, OSError, ValueError):
            real = open(os.devnull, "w")
        start_server.__defaults__ = (real,)


async def _load_mcp_tools():
    _ensure_server_stderr_has_fileno()
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
        _mcp_tools_cache = _run_sync(_load_mcp_tools())
    return next(t for t in _mcp_tools_cache if t.name == "geolocation")


def get_geolocation_tool():
    # The MCP-loaded tool only implements an async run method; the specialist
    # agents are invoked synchronously, so this wraps it in a plain sync tool.
    mcp_tool = _get_raw_mcp_tool()

    @tool
    def geolocation(ip: str) -> dict:
        """Look up the real country, region, city, and ISP for a public IP address via the live MCP geolocation server."""
        content = _run_sync(mcp_tool.ainvoke({"ip": ip}))
        # langchain-mcp-adapters returns MCP content blocks, not a plain dict:
        # unwrap the JSON text payload the FastMCP tool actually returned.
        return json.loads(content[0]["text"])

    return geolocation
