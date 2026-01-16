# Observer Summary

The observer feature adds a **read-only workspace summary** to prompts. It does not
execute tools and does not mutate files. When enabled, the backend injects an
`[AZ_OBSERVER]` block before the user message so the remote agent receives a compact
snapshot of the workspace.

## What it does
- Builds a snapshot of the workspace (file count, total bytes, sample tree lines).
- Adds a small summary block before `USER:` in the outbound prompt.
- Emits a status line in the UI/CLI when the observer summary is included.

## What it does NOT do
- It does **not** run tools or change files.
- It does **not** spawn a second Agent Zero session.
- It does **not** call external LLMs (provider fields are placeholders for future use).

## Configuration
- `observer.enabled`: enable or disable summaries.
- `observer.mode`:
  - `automatic`: include summary when workspace signature changes.
  - `always`: include summary on every prompt.
  - `manual`: never include summaries (disabled).

## UI/CLI access
- TUI: use `/observer` to open the observer status modal.
- CLI: use `/observer` or `/observer status` to view current settings.
- F5 opens the configured Agent Zero web UI when available.

## Output format
The summary block looks like:

```
[AZ_OBSERVER v1]
role: read-only workspace observer
policy: no tool execution, no file mutation
project: <name>
context_hash: <hash>
files: <count> total, <bytes> bytes
workspace_tree_sample:
- path/to/file.py (123B)
- ...
[/AZ_OBSERVER]
```
