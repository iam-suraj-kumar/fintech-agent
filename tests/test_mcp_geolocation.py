import asyncio

from tools.mcp_geolocation import _run_sync


async def _answer():
    await asyncio.sleep(0)
    return 42


def test_run_sync_without_event_loop():
    assert _run_sync(_answer()) == 42


def test_run_sync_inside_running_event_loop():
    # Jupyter runs cells inside an event loop, where asyncio.run() would raise.
    async def notebook_cell():
        return _run_sync(_answer())

    assert asyncio.run(notebook_cell()) == 42


def test_server_stderr_without_fileno_is_replaced():
    # Colab's notebook stderr has no file descriptor; the MCP server needs one.
    import io

    import mcp.client.stdio as stdio

    from tools.mcp_geolocation import _ensure_server_stderr_has_fileno

    start_server = stdio.stdio_client.__wrapped__
    saved = start_server.__defaults__
    try:
        start_server.__defaults__ = (io.StringIO(),)  # like Colab: fileno() raises
        _ensure_server_stderr_has_fileno()
        (errlog,) = start_server.__defaults__
        assert isinstance(errlog.fileno(), int)
    finally:
        start_server.__defaults__ = saved
