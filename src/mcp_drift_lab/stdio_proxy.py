from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


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


async def _pump(
    reader: asyncio.StreamReader,
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


async def run(command: list[str], log_path: Path) -> int:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    loop = asyncio.get_running_loop()
    stdin_reader = asyncio.StreamReader()
    stdin_protocol = asyncio.StreamReaderProtocol(stdin_reader)
    await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin.buffer)

    stdout_transport, stdout_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin,
        sys.stdout.buffer,
    )
    stdout_writer = asyncio.StreamWriter(stdout_transport, stdout_protocol, None, loop)
    lock = asyncio.Lock()

    await asyncio.gather(
        _pump(stdin_reader, process.stdin, "client_to_server", log_path, lock),
        _pump(process.stdout, stdout_writer, "server_to_client", log_path, lock),
    )
    return await process.wait()


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args.command, args.log)))


if __name__ == "__main__":
    main()
