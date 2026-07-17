from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class SinkEvent:
    event_id: str
    timestamp_utc: str
    manifest_id: str
    tool_name: str
    arguments: dict[str, Any]
    behavior: str


class SyntheticSink:
    """Append-only sink. It records intent but performs no external side effect."""

    def __init__(self, root: Path | None = None) -> None:
        lab_root = (root or Path(os.environ.get("MCP_DRIFT_ROOT", Path.cwd()))).resolve()
        run_id = os.environ.get("MCP_DRIFT_RUN_ID", "manual")
        configured = os.environ.get("MCP_DRIFT_SINK_FILE")
        self.path = (
            Path(configured)
            if configured
            else lab_root / "evidence" / "runs" / run_id / "synthetic-sink.jsonl"
        )

    def record(
        self,
        *,
        manifest_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        behavior: str,
    ) -> SinkEvent:
        event = SinkEvent(
            event_id=str(uuid4()),
            timestamp_utc=datetime.now(UTC).isoformat(),
            manifest_id=manifest_id,
            tool_name=tool_name,
            arguments=arguments,
            behavior=behavior,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True) + "\n")
        return event
