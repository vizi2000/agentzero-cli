# Issue List

This file contains issues to open for Agent Zero CLI and upstream Agent Zero.
Each item includes severity and acceptance criteria.

## Agent Zero CLI (this repo)

1) SECURITY: Prevent secret leaks in context previews
- Severity: critical
- Problem: context previews can include secrets if not redacted
- Fix: redact keys/patterns and skip sensitive files
- Acceptance: no secret values from `config.yaml` or `.env` appear in context

2) PROTOCOL: Persist and reuse context_id
- Severity: critical
- Problem: tool results are not sent if context_id is missing
- Fix: detect context_id in API responses (including alt keys)
- Acceptance: tool_result is sent with correct context_id

3) TOOLING: Send tool_result when user rejects a tool
- Severity: high
- Problem: agent may wait forever if rejection is not reported
- Fix: send ok=false tool_result with reason
- Acceptance: agent receives rejection event and continues

4) UX: Fix /upload and implement actual file copy
- Severity: high
- Problem: /upload does not copy file into workspace
- Fix: copy file into `workspace_root/uploads`
- Acceptance: /upload returns a path inside workspace

5) SECURITY: Honor whitelist in balanced mode
- Severity: medium
- Problem: whitelist is ignored by auto-approval logic
- Fix: auto-approve whitelisted shell commands
- Acceptance: shell tool auto-approves for whitelisted prefixes

6) UX: Respect show_timestamps/status_in_chat in new UI
- Severity: medium
- Problem: new UI ignores these config flags
- Fix: gate timestamps and status messages by config
- Acceptance: flags work as documented

7) DOCS: Align README with main entrypoint and shortcuts
- Severity: low
- Problem: README references legacy UI
- Fix: update README and docs
- Acceptance: README matches actual UI

## Agent Zero (upstream)

1) API: Standardize context_id field in responses
- Severity: high
- Problem: clients cannot reliably persist context_id
- Acceptance: documented response schema with context_id

2) API: Define tool_result schema for rejection
- Severity: high
- Problem: clients have no standard way to report rejection
- Acceptance: documented `ok=false` result with reason

3) API: Streaming format examples
- Severity: medium
- Problem: unclear SSE/JSONL payload formats
- Acceptance: examples in docs
