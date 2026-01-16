# Agent Zero CLI Operator Guide

This guide explains how to run, configure, and operate Agent Zero CLI/TUI safely, including the security model, tool approval workflow, and typical use cases. It also links to the next-steps specification (`docs/NEXT_STEPS_SPEC.md`) for additional context.

## Quick setup
1. Create a virtual environment and install dependencies:
   ```sh
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # optional: pip install -e .  # makes `pyproject` modules importable without PYTHONPATH
   ```
2. Configure connection secrets:
   - Copy `config.example.yaml` to `config.yaml`.
   - Set `connection.api_url` and use the `AGENTZERO_API_KEY` env var (never commit secrets).
   - Optionally override workspace/project settings per profile.
3. Run the application:
   - TUI: `python main_new.py`, `./a0tui`, or `./a0`
   - CLI: `python cli.py`, `./a0cli`, or `./a0 --cli`

## Runtime workflows
### Input and slash commands
- In the TUI, typing a prompt and pressing Enter sends it to Agent Zero; Shift+Enter starts a newline.
- `/upload <path>` copies the file into `<workspace_root>/uploads`, ensuring the agent works only on a local copy.

TUI commands (`a0tui` / `./a0`):
- `/help`, `/theme`, `/project`, `/agent`, `/new`, `/close`, `/clear`, `/upload`, `/status`, `/rename`, `/observer`

CLI commands (`a0cli` / `./a0 --cli`):
- `/help`, `/status`, `/mode`, `/security`, `/ai_observer`, `/observer`, `/context`, `/ml`, `/clear`, `/quit`

### Security modes and tool approvals
| Mode | Behavior |
| --- | --- |
| `paranoid` | Ask for approval on every tool request. |
| `balanced` | Auto-approve read-only tools (`read_file`, `list_files`, `search`) and whitelisted shell prefixes. |
| `god_mode` | Auto-approve all tool requests (use carefully). |

- CLI auto-approval lives in `cli/approval.py`: read-only tools are allowed automatically, shell commands are compared against the whitelist, and `/mode` lets you swap modes on the fly.
- UI shows a modal that previews the tool command, reason, and any content previews; you can “Explain” to request AI risk analysis.
- When rejecting a tool, the backend sends a `tool_result` with `ok=false` and a rejection reason so Agent Zero can continue.

### Context builder
- Enabled by default (`context.enabled=true`). Modes include `always`, `on_change`, `once`, and `manual`.
- Previews are limited by `context.max_preview_bytes` and filtered by `context.redact_keys`/`context.redact_patterns`. Sensitive files (`config.yaml`, `*.pem`, etc.) are excluded altogether.
- After the backend decides to send context, it mounts a status line summarizing file count, bytes, preview list, and hash.

## Testing and development
- Run tests with `PYTHONPATH=. pytest` (or `pytest` after `pip install -e .`). This ensures the CLI/TUI modules (e.g., `backend`, `cli`) resolve correctly.
- The `tests/test_e2e.py` suite spins up a mock SSE server to validate streaming + tool requests.
- During development, rerunning `./scripts/run_e2e.sh` reuses the mocked backend to keep the suite deterministic.

## Example use cases
1. **Security-conscious operator**: Switch to `paranoid`, run `/status` to confirm the stream, and respond to each tool request manually while rejecting anything touching the shell blacklist.
2. **Documentation auditor**: Keep `context.mode=on_change`, use `/upload spec.md` to add fresh files, and rely on auto-approved read-only tools and the live feed for status changes.
3. **Rapid prototyping**: Use CLI mode with `balanced` security, approve safe writes via previews, and inspect tool outputs in the console while editing the workspace.

## Troubleshooting
- If `/upload` says “File not found”, ensure the path points to an existing file and rerun the slash command.
- If the backend complains about context or secrets, double-check `context.redact_keys`/`redact_patterns` and the workspace root.
- When tests fail with `ModuleNotFoundError`, run `PYTHONPATH=. pytest` or install the package (`pip install -e .`).

## Community and feedback
See `docs/NEXT_STEPS_SPEC.md` for the outreach plan, and use the templates in `docs/COMMUNITY.md` (Polish/English) to announce the Beta release, share the repo (`https://github.com/agentzero/AgentZeroCLI`), and point people at the docs + issue tracker.
