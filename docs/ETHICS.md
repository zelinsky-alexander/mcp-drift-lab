# Ethics and responsible testing

## Allowed scope

- Clients, accounts, machines, and MCP servers controlled by the researcher
- Explicitly opt-in maintainers and research participants
- Passive collection of public registry metadata subject to applicable terms and rate limits
- Harmless synthetic canaries and local append-only sinks

## Out of scope

- Invoking tools on third-party MCP servers without authorization
- Authentication bypass, credential collection, or access-token reuse
- Reading personal files, inboxes, repositories, cloud resources, or production databases
- Sending real messages, financial transactions, trades, or destructive commands
- Deceptive publication of client or vendor claims without versioned reproducible evidence

## Minimum-impact principles

1. Record exact client, model, protocol, server, and harness versions.
2. Use fresh test profiles and synthetic identities.
3. Store the least evidence necessary.
4. Redact tokens, personal data, and unrelated conversation content.
5. Reproduce a finding before disclosure.
6. Give vendors reasonable time to investigate high-impact findings.
7. Distinguish protocol behavior, client behavior, and model behavior.
8. Do not label a product vulnerable solely because an LLM followed a synthetic instruction.

## Disclosure package

A vendor report should contain the smallest reproducible scenario, exact version information, expected versus observed behavior, hashes of before/after toolsets, sanitized protocol traces, screenshots, impact analysis, and a proposed mitigation.
