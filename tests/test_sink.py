import json
from pathlib import Path

from mcp_drift_lab.sink import SyntheticSink


def test_sink_records_without_external_side_effect(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MCP_DRIFT_RUN_ID", "test-run")
    sink = SyntheticSink(tmp_path)
    event = sink.record(
        manifest_id="v0-benign",
        tool_name="write_demo_note",
        arguments={"note": "SYNTHETIC_SECRET_7F92"},
        behavior="append-synthetic-note",
    )
    target = tmp_path / "evidence" / "runs" / "test-run" / "synthetic-sink.jsonl"
    row = json.loads(target.read_text(encoding="utf-8"))
    assert row["event_id"] == event.event_id
    assert row["arguments"]["note"] == "SYNTHETIC_SECRET_7F92"
