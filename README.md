# Agent Zero CLI (Beta)

[![CI](https://github.com/vizi2000/agentzero-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/vizi2000/agentzero-cli/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/vizi2000/agentzero-cli)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/agentzero-cli)](https://pypi.org/project/agentzero-cli/)

A secure local CLI/TUI operator console for Agent Zero. It adds a human-in-the-loop
approval gate, context builder, and a polished Textual UI so you can safely run agents
against local workspaces. Ideal for AI agent safety, tool approval workflows, and
local-first automation.

> **Status:** Beta — features are stable but evolving. Please report issues and feedback.

## Why this project
- Run Agent Zero from your own terminal with explicit tool approvals.
- Keep your workspace local while providing safe context to the agent.
- Switch between a full TUI and a lightweight CLI depending on the task.

## Keywords
Agent Zero CLI, AI agent safety, human-in-the-loop tooling, secure agent execution,
local-first AI, Textual TUI, Rich CLI, tool approval workflow, context injection.

## Features
- **Security modes** — `paranoid`, `balanced`, `god_mode`
- **Tool approvals** — preview and approve writes + shell
- **Context builder** — tree, previews, git status, redaction
- **Observer summaries** — read-only workspace snapshot injected into prompts
- **Dual UI** — Textual TUI + Rich CLI
- **Themes + arcade** — retro themes and waiting game (TUI)

## Quick start
```bash
pip install agentzero-cli
```

First run (creates config on first launch):
```bash
a0cli
# or
 a0tui
```

Local repo wrapper:
```bash
./a0        # TUI
./a0 --cli  # CLI
```

## Configuration
Main config file: `config.yaml` (or `~/.config/agentzero/config.yaml`).

Minimal example:
```yaml
connection:
  api_url: "http://localhost:50001/api_message"
  ui_url: "http://localhost:50001/"
  api_key: "your_api_key"

security:
  mode: "balanced"  # paranoid | balanced | god_mode
  allow_shell: false
  whitelist: ["git", "npm", "pip"]
  blacklist_patterns: ["rm -rf", "sudo"]

ui:
  theme: "Studio Dark"
  waiting_game: "invaders"  # invaders | pong | off
```

See `docs/CONFIGURATION.md` for full reference.

## Usage
### TUI (`a0tui` / `./a0`)
- F1 Help, F2 Menu, F3 Game, F5 Web UI, F10 Quit
- Slash commands: `/help`, `/theme`, `/project`, `/agent`, `/new`, `/close`, `/clear`,
  `/upload`, `/status`, `/observer`

### CLI (`a0cli` / `./a0 --cli`)
```
/help              - Show help
/status            - Connection and config status
/mode              - Interactive security mode selector
/security          - Security settings menu
/ai_observer       - Observer/LLM settings
/observer [info]   - Observer status
/context           - Context status
/ml                - Multiline input
/clear             - Clear chat history
/quit              - Exit CLI
```

## Security model (summary)
- `paranoid`: approve every tool
- `balanced`: auto-approve read-only + whitelisted shell prefixes
- `god_mode`: auto-approve all tools

`blacklist_patterns` are always enforced for shell commands.

## Development
```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

ruff check .
black --check .
pytest tests/
```

## Documentation
- `docs/SPEC.md`
- `docs/CONFIGURATION.md`
- `docs/SECURITY.md`
- `docs/USAGE.md`
- `docs/OPERATOR_GUIDE.md`

## License
MIT — see `LICENSE`.
