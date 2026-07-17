from __future__ import annotations

import argparse
import json

from .manifests import ManifestError, ManifestStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage MCP Drift Lab experiment state")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show the selected manifest and hashes")
    sub.add_parser("hashes", help="Print machine-readable hashes")
    sub.add_parser("list-manifests", help="List available experiment manifests")
    set_state = sub.add_parser("set-state", help="Atomically select a manifest")
    set_state.add_argument("manifest")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ManifestStore()
    try:
        if args.command == "list-manifests":
            print("\n".join(store.list_manifests()))
            return
        if args.command == "set-state":
            store.set_current(args.manifest)
            print(f"Selected {args.manifest}")
            return

        loaded = store.load_current()
        data = {
            "manifest": loaded.path.name,
            "manifest_id": loaded.raw["id"],
            "manifest_hash": loaded.manifest_hash,
            "toolset_hash": loaded.toolset_hash,
            "tool_names": [tool["name"] for tool in loaded.tools],
        }
        if args.command == "hashes":
            print(json.dumps(data, sort_keys=True))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    except ManifestError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
