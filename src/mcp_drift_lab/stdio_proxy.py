from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record newline-delimited MCP stdio traffic")
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a child command is required after --")
    return args


async def _record(
    log_path: Path,
    direction: str,
    payload: bytes,
    lock: asyncio.Lock,
) -> None:
    entry = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "direction": direction,
        "raw": payload.decode("utf-8", errors="replace").rstrip("\r\n"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    async with lock:
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


class _ThreadedLineReader:
    """Read a parent stdio stream without requiring an asyncio pipe transport.

    Windows console handles cannot reliably be registered with asyncio's pipe
    APIs.  The thread is deliberately daemonized because a blocking read from a
    parent client cannot be cancelled by Python; it must never hold proxy
    shutdown hostage after the child has gone away.
    """

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._loop = asyncio.get_running_loop()
        self._lines: asyncio.Queue[bytes | BaseException] = asyncio.Queue(maxsize=1)
        self._next_line = threading.Event()
        self._next_line.set()
        self._thread = threading.Thread(target=self._read_lines, daemon=True)
        self._thread.start()

    def _read_lines(self) -> None:
        while True:
            self._next_line.wait()
            self._next_line.clear()
            try:
                line = self._stream.readline()
            except BaseException as error:
                self._loop.call_soon_threadsafe(self._lines.put_nowait, error)
                return
            self._loop.call_soon_threadsafe(self._lines.put_nowait, line)
            if not line:
                return

    async def readline(self) -> bytes:
        result = await self._lines.get()
        self._next_line.set()
        if isinstance(result, BaseException):
            raise result
        return result


async def _write_and_flush(stream: BinaryIO, payload: bytes) -> None:
    def write() -> None:
        stream.write(payload)
        stream.flush()

    await asyncio.to_thread(write)


async def _pump_client_to_server(
    reader: _ThreadedLineReader,
    writer: asyncio.StreamWriter,
    direction: str,
    log: Path,
    lock: asyncio.Lock,
) -> None:
    while line := await reader.readline():
        await _record(log, direction, line, lock)
        writer.write(line)
        await writer.drain()
    try:
        writer.write_eof()
    except (AttributeError, OSError):
        pass


async def _pump_server_to_client(
    reader: asyncio.StreamReader,
    stdout: BinaryIO,
    direction: str,
    log: Path,
    lock: asyncio.Lock,
) -> None:
    while line := await reader.readline():
        await _record(log, direction, line, lock)
        await _write_and_flush(stdout, line)


async def _close_child_stdin(process: asyncio.subprocess.Process) -> None:
    if process.stdin is None or process.stdin.is_closing():
        return
    process.stdin.close()
    try:
        await process.stdin.wait_closed()
    except (AttributeError, OSError):
        pass


async def _terminate_child(process: asyncio.subprocess.Process) -> None:
    await _close_child_stdin(process)
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except TimeoutError:
        process.kill()
        await process.wait()


async def run(
    command: list[str],
    log_path: Path,
    parent_stdin: BinaryIO | None = None,
    parent_stdout: BinaryIO | None = None,
) -> int:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    client_stdin = parent_stdin if parent_stdin is not None else sys.stdin.buffer
    client_stdout = parent_stdout if parent_stdout is not None else sys.stdout.buffer
    stdin_reader = _ThreadedLineReader(client_stdin)
    lock = asyncio.Lock()
    client_pump = asyncio.create_task(
        _pump_client_to_server(
            stdin_reader, process.stdin, "client_to_server", log_path, lock
        )
    )
    server_pump = asyncio.create_task(
        _pump_server_to_client(
            process.stdout, client_stdout, "server_to_client", log_path, lock
        )
    )
    process_wait = asyncio.create_task(process.wait())

    try:
        done, _ = await asyncio.wait(
            {client_pump, server_pump, process_wait},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if client_pump in done:
            await client_pump
            await _close_child_stdin(process)
            try:
                await asyncio.wait_for(asyncio.shield(process_wait), timeout=2)
            except TimeoutError:
                await _terminate_child(process)
            await server_pump
        else:
            if server_pump in done:
                await server_pump
            await _terminate_child(process)
            client_pump.cancel()
            await asyncio.gather(client_pump, return_exceptions=True)
            await server_pump
        return process.returncode if process.returncode is not None else await process_wait
    finally:
        for task in (client_pump, server_pump, process_wait):
            if not task.done():
                task.cancel()
        await asyncio.gather(client_pump, server_pump, process_wait, return_exceptions=True)
        await _terminate_child(process)


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args.command, args.log)))


if __name__ == "__main__":
    main()
