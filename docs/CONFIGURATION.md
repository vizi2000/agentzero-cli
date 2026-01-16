# Configuration Reference

This project loads `config.yaml` from the repo root or `~/.config/agentzero/config.yaml`.
Do not store secrets in it. Prefer environment variables: `AGENTZERO_API_URL`, `AGENTZERO_API_KEY`.

## connection
- `api_url` (string): HTTP endpoint for Agent Zero API.
- `api_key` (string): API key (prefer env var).
- `ui_url` (string): Agent Zero web UI URL (used by F5).
- `dashboard_url` (string): optional alias for `ui_url`.
- `host`/`port`/`path` (string/int): optional pieces if `api_url` is not provided.
- `workspace_root` (string): base path for tool access.
- `stream` (bool): enable streaming.
- `stream_mode` (auto|sse|jsonl): streaming mode.
- `timeout_seconds` (int): 0 means no timeout.
- `keepalive_seconds` (float): status heartbeat interval.
- `max_wait_seconds` (float): optional hard wait limit.

## projects
Allows multiple workspaces and project switching.

## agent_profiles
Map of profile name to prompt/instructions.

## context
- `enabled` (bool)
- `mode` (always|on_change|once|manual)
- `max_bytes`, `max_files`, `max_depth`
- `include_tree`, `include_previews`, `include_git`, `include_system`, `include_tools`
- `preview_files`: list of files to preview
- `max_preview_bytes`
- `redact_keys`: keys to mask in previews
- `redact_patterns`: regex patterns to mask in previews

## security
- `mode` (paranoid|balanced|god_mode)
- `allow_shell` (bool)
- `whitelist`: command prefixes auto-approved in balanced mode
- `blacklist_patterns`: denylist for shell commands

## ui
- `theme`
- `waiting_game` (invaders|pong|off)
- `show_timestamps` (bool)
- `status_in_chat` (bool)

## observer
- `enabled` (bool): include a read-only observer summary in prompts.
- `mode` (automatic|manual|always): when observer summaries refresh.
- `type` (agent_zero|local_llm): reserved for future LLM observers.
- `provider` (agent_zero|openai|openrouter|local): stored for UI/CLI menus.
- `model` (string): model ID placeholder for future LLM observers.
- `api_key` (string): API key for remote providers (prefer env vars).
- `endpoint` (string): optional override for OpenRouter or other host.
- `path` (string): local model binary or server address when `type=local_llm`.

Observer summaries are generated locally from workspace snapshots; provider/model fields
are currently informational and may be wired to LLM observers later.

## Example
See `config.example.yaml`.
