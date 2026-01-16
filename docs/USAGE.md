# Usage Guide

## Start
1) Install deps: `pip install -r requirements.txt`
   - For development: `pip install -e ".[dev]"`
2) Copy `config.example.yaml` to `config.yaml` and set API URL/KEY
3) Run: `python main_new.py`, `./a0tui`, or `./a0`

CLI mode:
- `python cli.py`
- `./a0cli`
- `./a0 --cli`

## UI basics
- Enter: send prompt
- Shift+Enter: newline
- F1: help
- F2: menu
- F3: game
- F10: quit

## Menu
The menu lets you switch:
- Project
- Agent profile
- Theme
- Actions: clear chat, new tab, upload file, status

## Slash commands

TUI (`a0tui` / `./a0`):
- `/help` list commands
- `/theme <name>` switch theme
- `/project <name>` switch project
- `/agent <name>` switch profile
- `/new [name]` new chat tab
- `/close` close current tab
- `/clear` clear current chat
- `/upload [path]` copy file into workspace `uploads/`
- `/status` show connection status
- `/observer [info]` observer modal or status

CLI (`a0cli` / `./a0 --cli`):
- `/help` list commands
- `/status` show connection status
- `/mode` change security mode
- `/security` security settings menu
- `/ai_observer` observer/LLM settings menu
- `/observer [info]` observer status
- `/context` context status
- `/ml` multi-line input
- `/clear`, `/quit`

## Observer menu & keys
- F5 opens the configured Agent Zero web UI for quick verification
- F2 menu → Observer Settings opens a summary modal and exposes the current config

## Tool approvals
When the agent requests a tool:
- Approve to execute
- Reject to skip (a rejection result is sent to Agent Zero)
- Explain to show risk analysis

## Troubleshooting
- No stream: check `stream=true` and server support.
- Tool blocked: check `allow_shell` and blacklist.
- No context: check `context.enabled` and `context.mode`.
