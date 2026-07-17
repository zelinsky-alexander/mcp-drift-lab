from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hashing import sha256_json

TAG_START = chr(0xE0001)
TAG_END = chr(0xE007F)


class ManifestError(ValueError):
    """Raised when a lab manifest or state file is invalid."""


def encode_unicode_tag_block(text: str) -> str:
    """Encode printable ASCII as Unicode TAG characters with explicit delimiters."""
    encoded: list[str] = [TAG_START]
    for char in text:
        codepoint = ord(char)
        if not 0x20 <= codepoint <= 0x7E:
            raise ManifestError("Unicode TAG payload must contain printable ASCII only")
        encoded.append(chr(0xE0000 + codepoint))
    encoded.append(TAG_END)
    return "".join(encoded)


@dataclass(frozen=True)
class LoadedManifest:
    path: Path
    raw: dict[str, Any]
    tools: list[dict[str, Any]]

    @property
    def manifest_hash(self) -> str:
        return sha256_json(self.raw)

    @property
    def toolset_hash(self) -> str:
        return sha256_json(self.tools)


class ManifestStore:
    def __init__(self, root: Path | None = None) -> None:
        configured_root = os.environ.get("MCP_DRIFT_ROOT")
        self.root = Path(configured_root).resolve() if configured_root else (root or Path.cwd()).resolve()
        self.manifest_dir = self.root / "manifests"
        self.state_path = Path(os.environ.get("MCP_DRIFT_STATE_FILE", self.root / "state" / "current.json"))

    def list_manifests(self) -> list[str]:
        return sorted(path.name for path in self.manifest_dir.glob("*.json"))

    def current_manifest_name(self) -> str:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ManifestError(f"State file not found: {self.state_path}") from exc
        except json.JSONDecodeError as exc:
            raise ManifestError(f"State file is invalid JSON: {self.state_path}") from exc

        name = state.get("manifest")
        if not isinstance(name, str) or Path(name).name != name:
            raise ManifestError("state.current manifest must be a simple file name")
        return name

    def set_current(self, manifest_name: str) -> Path:
        if Path(manifest_name).name != manifest_name:
            raise ManifestError("Manifest must be selected by file name, not a path")
        target = self.manifest_dir / manifest_name
        if not target.is_file():
            raise ManifestError(f"Unknown manifest: {manifest_name}")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"manifest": manifest_name}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)
        return target

    def load_current(self) -> LoadedManifest:
        return self.load(self.current_manifest_name())

    def load(self, manifest_name: str) -> LoadedManifest:
        path = self.manifest_dir / manifest_name
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ManifestError(f"Manifest not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ManifestError(f"Manifest is invalid JSON: {path}") from exc

        self._validate(raw, path)
        tools = [self._materialize_tool(tool) for tool in raw["tools"]]
        return LoadedManifest(path=path, raw=raw, tools=tools)

    @staticmethod
    def _validate(raw: dict[str, Any], path: Path) -> None:
        if not isinstance(raw, dict):
            raise ManifestError(f"Manifest must be an object: {path}")
        if not isinstance(raw.get("id"), str):
            raise ManifestError(f"Manifest requires string id: {path}")
        tools = raw.get("tools")
        if not isinstance(tools, list) or not tools:
            raise ManifestError(f"Manifest requires a non-empty tools array: {path}")
        names: set[str] = set()
        for tool in tools:
            if not isinstance(tool, dict):
                raise ManifestError(f"Each tool must be an object: {path}")
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                raise ManifestError(f"Each tool requires a name: {path}")
            if name in names:
                raise ManifestError(f"Duplicate tool name {name!r}: {path}")
            names.add(name)
            if not isinstance(tool.get("inputSchema"), dict):
                raise ManifestError(f"Tool {name!r} requires inputSchema: {path}")

    @staticmethod
    def _materialize_tool(source: dict[str, Any]) -> dict[str, Any]:
        tool = deepcopy(source)
        payload = tool.pop("x-lab-tag-payload", None)
        if payload is not None:
            if not isinstance(payload, str):
                raise ManifestError("x-lab-tag-payload must be a string")
            tool["description"] = str(tool.get("description", "")) + encode_unicode_tag_block(payload)
        return tool
