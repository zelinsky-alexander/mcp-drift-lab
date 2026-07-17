# MCP Drift Lab

MCP Drift Lab is a controlled, non-destructive research harness for measuring whether real Model Context Protocol clients preserve informed consent when tool definitions change after approval.

The project intentionally separates two questions:

1. **Client lifecycle security:** Did the client fetch, detect, display, re-approve, and gate a changed definition?
2. **Model susceptibility:** After receiving changed metadata, did the model select a tool or alter its arguments?

All tools operate only on synthetic data and append events to a local JSONL sink. No real email, filesystem, cloud, trading, or identity account is connected.

## Current scope

- File-backed, dynamically materialized MCP tool manifests
- Six baseline states: benign, description mutation, schema mutation, tool addition, Unicode TAG concealment, and behavior-only mutation
- Local stdio transport
- Streamable HTTP transport for controlled remote-client testing
- Optional lab-only control tool that emits `notifications/tools/list_changed`
- Canonical whole-manifest and on-wire toolset hashes
- Transparent stdio JSONL recorder
- Synthetic execution sink
- Pytest coverage and GitHub Actions CI
- Detailed cross-client research plan in [`TEST_PLAN.md`](TEST_PLAN.md)

## Safety boundary

This repository is for testing clients you own or are explicitly authorized to test. Do not invoke tools on third-party MCP servers, attempt authentication bypass, collect credentials, or connect the harness to production accounts. See [`docs/ETHICS.md`](docs/ETHICS.md).

## Requirements

- Python 3.11+
- `uv` recommended, or standard `venv`/`pip`
- Node.js 22.7.5+ only when using MCP Inspector

The project pins MCP Python SDK v1 because v2 remains prerelease until its stable release. The upper bound prevents an unreviewed major-version upgrade from changing experiment behavior.

## Install

### With uv

```bash
uv sync --extra dev
```

### With venv and pip

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/WSL: source .venv/bin/activate
pip install -e ".[dev]"
```

## Inspect the current state

```bash
mcp-drift status
mcp-drift hashes
mcp-drift list-manifests
```

The default state is `v0-benign.json`.

## Switch experiment state

```bash
mcp-drift set-state v1-description-mutation.json
mcp-drift status
```

The server reads the selected manifest on every `tools/list`, so a client refresh sees the new definition without restarting the process.

## Run over stdio

```bash
mcp-drift-server --transport stdio
```

Example VS Code `.vscode/mcp.json` entry:

```json
{
  "servers": {
    "mcp-drift-lab": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "mcp-drift-server", "--transport", "stdio"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## Run with raw stdio recording

Configure the client to launch the proxy instead of the server:

```bash
mcp-drift-proxy --log evidence/runs/manual/jsonrpc.jsonl -- \
  uv run mcp-drift-server --transport stdio
```

The proxy preserves protocol stdout and writes timestamped client-to-server and server-to-client messages to JSONL.

## Run over Streamable HTTP

```bash
mcp-drift-server --transport streamable-http --host 127.0.0.1 --port 8000
```

Connect MCP Inspector to:

```text
http://127.0.0.1:8000/mcp
```

For a public deployment, terminate TLS in a reverse proxy and keep the state-control path local. The server has no public mutation-control HTTP endpoint.

## Emit `tools/list_changed`

For protocol-baseline experiments only, enable the explicit control tool:

```bash
MCP_DRIFT_ENABLE_CONTROL_TOOL=1 mcp-drift-server --transport stdio
```

Then:

1. Change state externally with `mcp-drift set-state ...`.
2. Call `lab_emit_tool_list_changed` from MCP Inspector.
3. Observe whether the client requests `tools/list` again.

Do not enable this tool in approval-fidelity experiments because its presence changes the advertised toolset.

## Run MCP Inspector

```bash
npx -y @modelcontextprotocol/inspector@latest
```

For a direct stdio launch:

```bash
npx -y @modelcontextprotocol/inspector@latest \
  uv run mcp-drift-server --transport stdio
```

Keep Inspector bound to localhost and retain its proxy authentication. Never expose the Inspector proxy to an untrusted network.

## Run tests

```bash
pytest
ruff check .
```

## Evidence

Each tool call is appended to `evidence/runs/<run-id>/synthetic-sink.jsonl` when `MCP_DRIFT_RUN_ID` is set. Otherwise it is written beneath `evidence/runs/manual/`.

Suggested run setup:

```bash
export MCP_DRIFT_RUN_ID=vs-code-v0-v1-live-001
mcp-drift-server --transport stdio
```

Copy the row template from [`evidence/results-template.csv`](evidence/results-template.csv) into your analysis dataset and add screenshots, client logs, prompts, and version metadata under the matching run directory.

## Repository layout

```text
mcp-drift-lab/
├── manifests/                  # Experiment definitions
├── scenarios/                  # Test matrix inputs
├── state/current.json          # Selected manifest
├── src/mcp_drift_lab/          # Server, CLI, hashing, sink, recorder
├── evidence/                   # Result schema and ignored run output
├── tests/                      # Deterministic unit tests
├── docs/ETHICS.md              # Research boundaries
└── TEST_PLAN.md                # Latest cross-client test plan
```
