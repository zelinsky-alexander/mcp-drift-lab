# Evidence handling

Create one directory per run under `evidence/runs/<run-id>/`. Run contents are ignored by Git because screenshots, recordings, model outputs, and traces may be large or sensitive.

Recommended files:

- `metadata.json`
- `server-v0.json`
- `server-v1.json`
- `jsonrpc.jsonl`
- `server.log`
- `client.log`
- `approval-before.png`
- `approval-after.png`
- `prompt.txt`
- `response.txt`
- `synthetic-sink.jsonl`

Never commit real credentials, access tokens, private conversations, or unrelated user data. Publish only reviewed, minimized evidence.
