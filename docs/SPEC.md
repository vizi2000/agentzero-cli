# Agent Zero CLI Specification

## 1. Scope
Agent Zero CLI is a local TUI proxy for Agent Zero. It accepts user prompts,
optionally augments them with workspace context, sends them to Agent Zero API,
streams back events, and executes local tools only with user approval.

## 2. Goals
- Provide a secure, local operator panel for Agent Zero.
- Keep a human-in-the-loop gate for tool execution.
- Build context from workspace safely and deterministically.
- Support streaming responses (SSE or JSONL).

## 3. Non-goals
- Replace Agent Zero server logic.
- Execute tools without user control unless explicitly configured.
- Store secrets in the repo.

## 4. Components
- UI (Textual): chat view, live feed, status cards, themes, mini-arcade.
- Backend proxy: HTTP client, event normalization, tool dispatching.
- Context builder: file tree, preview, git status.
- Tool execution: read/list/search/write/replace/patch/shell (optional).

## 5. External API
### 5.1 Request
POST to `connection.api_url` with JSON:
```
{
  "message": "<prompt with optional context>",
  "lifetime_hours": 24,
  "context_id": "optional"
}
```

### 5.2 Response
Supported formats:
- SSE (`text/event-stream`)
- JSONL / NDJSON
- Plain JSON or string

### 5.3 Event Types
The proxy normalizes responses into events:
- `status`: status line for operator UI
- `thinking` / `thought`: reasoning stream (optional)
- `tool_request`: request to run a tool locally
- `tool_output`: output from tool execution
- `final_response`: final answer from Agent Zero

### 5.4 Context ID
If the response includes `context_id` (or `contextId`, `conversation_id`), the
proxy stores it and attaches to future requests and tool results.

## 6. Tool Calls
### 6.1 Tool request schema
```
{
  "type": "tool_request",
  "tool_name": "read_file|list_files|search_text|write_file|replace_text|apply_patch|shell",
  "command": "human-readable command string",
  "reason": "why it is needed",
  "payload": { ... tool args ... }
}
```

### 6.2 Tool result schema
```
{
  "tool_name": "read_file",
  "ok": true,
  "output": "...",
  "details": { ... },
  "tool_call_id": "optional id"
}
```

If the user rejects a tool, the proxy sends `ok=false` with a rejection reason.

## 7. Context Builder
### 7.1 Modes
- `always`: always send context
- `on_change`: send only if signature changes
- `once`: send once per context_id
- `manual`: never auto-send context

### 7.2 Content
- File tree (bounded by depth and max files)
- Optional file previews
- Optional git status
- Optional system metadata

### 7.3 Redaction
Preview content is redacted using:
- `context.redact_keys`: key names to mask in YAML/JSON
- `context.redact_patterns`: regex patterns to replace with `***REDACTED***`

Sensitive files (like `config.yaml` or `.env`) are excluded by default.

## 8. Security Model
- `paranoid`: ask for every tool
- `balanced`: auto-approve read-only and whitelisted shell
- `god_mode`: auto-approve all tools

Default guidance:
- `allow_shell=false` by default; enabling shell execution logs a warning.
- `blacklist_patterns` are always enforced for shell commands.
- Use `whitelist` to auto-approve known-safe shell prefixes in balanced mode.

## 9. UI Requirements
- Must display live feed of events and status.
- Must show tool approval dialog with preview.
- Must support project/profile/theme switching.
- Must handle both single-line and multi-line input.

## 10. Error Handling
- Network errors show as `final_response` with error summary.
- Tool failures return `ok=false` with stderr in `output`.

## 11. Performance Constraints
- Context size bounded by `context.max_bytes`.
- File previews bounded by `context.max_preview_bytes`.

## 12. Compatibility
- Python 3.10+ recommended.
- Textual >= 0.40.0
