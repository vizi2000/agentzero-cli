# Project Summary - Agent Zero CLI

## Purpose
Agent Zero CLI provides a secure terminal interface (CLI + TUI) for Agent Zero, with
human-in-the-loop approvals, observer summaries, and a consistent operator workflow.

## Key Entry Points
- CLI: `a0cli` or `python -m cli`
- TUI: `a0tui` or `python -m main_new`
- Local wrapper: `./a0` (defaults to TUI)

## Core Modules
- `backend.py` — Agent Zero client + context builder
- `cli/` — CLI interface and slash commands
- `ui/` — Textual-based TUI
- `observer/` — Tool routing and observer logic
- `llm_providers/` — LLM integration adapters

## Configuration & Env
- Config files: `config.yaml`, `config.example.yaml`
- Global config: `~/.config/agentzero/config.yaml` (created on first run)
- Env vars: prefixed with `AGENTZERO_`
- MCP gateway API key: `MCP_GATEWAY_API_KEY` (if used)

## Common Commands
- Install (dev): `pip install -e ".[dev]"`
- Run CLI: `a0cli`
- Run TUI: `a0tui`
- Tests: `pytest tests/`
- Lint: `ruff check .`
- Format check: `black --check .`

## Deployment Info
- Primary server: `theones.io` (194.181.240.37)
- SSH: `vizi@borg.tools`
- Agent Zero URL: `http://194.181.240.37:50001/` (may be offline)
- MCP SSE endpoint: `http://194.181.240.37:50001/mcp/.../sse` (project-specific)

## MCP / Tooling Notes
- opencode MCP config lives in `~/.opencode/config.json` (local machine)
- MCP Gateway tools available via `tools/call` on `https://mcp.borg.tools`
- Context7 MCP is required before new 3rd-party libraries

## Current Status
- Active development, beta status

## Update Rule (Required)
- If no summary exists, create one and store it in local docs and MCP memory.
- On any larger change (new module, config, deployment, or workflow change), update
  this summary and re-append it to MCP memory for the `AgentZeroCLI` subject.
