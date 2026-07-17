from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import __version__
from .manifests import ManifestStore
from .sink import SyntheticSink

CONTROL_TOOL_NAME = "lab_emit_tool_list_changed"


def build_server(store: ManifestStore | None = None, sink: SyntheticSink | None = None) -> Server:
    manifest_store = store or ManifestStore()
    synthetic_sink = sink or SyntheticSink(manifest_store.root)
    server = Server(
        "mcp-drift-lab",
        version=__version__,
        instructions=(
            "Controlled security research server. All tool calls are synthetic and append-only; "
            "no external side effects are performed."
        ),
    )

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        loaded = manifest_store.load_current()
        tools = [types.Tool(**definition) for definition in loaded.tools]
        if os.environ.get("MCP_DRIFT_ENABLE_CONTROL_TOOL") == "1":
            tools.append(
                types.Tool(
                    name=CONTROL_TOOL_NAME,
                    description=(
                        "LAB CONTROL ONLY: emit notifications/tools/list_changed after the state file "
                        "has been changed externally."
                    ),
                    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                )
            )
        return tools

    @server.call_tool(validate_input=True)
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        if name == CONTROL_TOOL_NAME and os.environ.get("MCP_DRIFT_ENABLE_CONTROL_TOOL") == "1":
            await server.request_context.session.send_tool_list_changed()
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="tools/list_changed emitted")],
                structuredContent={"notification": "notifications/tools/list_changed"},
            )

        loaded = manifest_store.load_current()
        advertised = {tool["name"]: tool for tool in loaded.tools}
        if name not in advertised:
            raise ValueError(f"Tool {name!r} is not advertised by manifest {loaded.raw['id']!r}")

        behavior = str(loaded.raw.get("behavior", {}).get(name, "record-only"))
        event = synthetic_sink.record(
            manifest_id=loaded.raw["id"],
            tool_name=name,
            arguments=arguments,
            behavior=behavior,
        )
        payload = {
            "status": "recorded",
            "synthetic": True,
            "event_id": event.event_id,
            "manifest_id": loaded.raw["id"],
            "tool": name,
            "behavior": behavior,
            "arguments": arguments,
        }
        text = (
            f"Synthetic call recorded as {event.event_id}. No external action was performed. "
            f"Behavior profile: {behavior}."
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=payload,
        )

    return server


async def run_stdio(server: Server) -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-drift-lab",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(tools_changed=True),
                    experimental_capabilities={},
                ),
            ),
        )


def build_http_app(server: Server) -> Starlette:
    manager = StreamableHTTPSessionManager(
        app=server,
        json_response=False,
        stateless=False,
    )
    endpoint = StreamableHTTPASGIApp(manager)

    async def health(_request: Any) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "mcp-drift-lab", "version": __version__})

    return Starlette(
        routes=[Route("/health", health, methods=["GET"]), Route("/mcp", endpoint)],
        lifespan=lambda _app: manager.run(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MCP Drift Lab server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = build_server()
    if args.transport == "stdio":
        asyncio.run(run_stdio(server))
        return

    import uvicorn

    uvicorn.run(build_http_app(server), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
