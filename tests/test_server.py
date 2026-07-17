from pathlib import Path

import mcp.types as types
import pytest

from mcp_drift_lab.manifests import ManifestStore
from mcp_drift_lab.server import build_server
from mcp_drift_lab.sink import SyntheticSink


@pytest.mark.asyncio
async def test_server_lists_current_manifest_tools(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("MCP_DRIFT_SINK_FILE", str(tmp_path / "sink.jsonl"))
    store = ManifestStore(root)
    server = build_server(store, SyntheticSink(root))

    handler = server.request_handlers[types.ListToolsRequest]
    result = await handler(types.ListToolsRequest(method="tools/list"))
    names = [tool.name for tool in result.root.tools]
    assert names == ["read_demo_record", "write_demo_note"]
