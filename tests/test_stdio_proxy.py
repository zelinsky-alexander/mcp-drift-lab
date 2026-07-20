import asyncio
import io
import json
import sys
import threading
from pathlib import Path

import pytest

from mcp_drift_lab.stdio_proxy import run


@pytest.mark.asyncio
async def test_proxy_forwards_and_records_binary_lines(tmp_path: Path) -> None:
    payload = b'{"jsonrpc":"2.0","method":"tools/list"}\n'
    client_stdin = io.BytesIO(payload)
    client_stdout = io.BytesIO()
    child = (
        "import sys; "
        "line = sys.stdin.buffer.readline(); "
        "sys.stdout.buffer.write(line); sys.stdout.buffer.flush()"
    )

    result = await run(
        [sys.executable, "-u", "-c", child],
        tmp_path / "traffic.jsonl",
        client_stdin,
        client_stdout,
    )

    assert result == 0
    assert client_stdout.getvalue() == payload
    rows = [
        json.loads(line)
        for line in (tmp_path / "traffic.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["direction"] for row in rows] == ["client_to_server", "server_to_client"]
    assert [row["raw"] for row in rows] == [
        '{"jsonrpc":"2.0","method":"tools/list"}',
        '{"jsonrpc":"2.0","method":"tools/list"}',
    ]
    assert all(row["timestamp_utc"] for row in rows)


@pytest.mark.asyncio
async def test_proxy_cancellation_terminates_child_with_blocking_parent_input(
    tmp_path: Path,
) -> None:
    release_input = threading.Event()

    class BlockingInput:
        def readline(self) -> bytes:
            release_input.wait()
            return b""

    task = asyncio.create_task(
        run(
            [sys.executable, "-u", "-c", "import time; time.sleep(60)"],
            tmp_path / "traffic.jsonl",
            BlockingInput(),
            io.BytesIO(),
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release_input.set()
