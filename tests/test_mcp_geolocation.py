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
