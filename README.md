# Agent Zero CLI

> AI coding agent with security interceptor - your prompts, your machine, your control.

[![PyPI version](https://badge.fury.io/py/agentzero-cli.svg)](https://pypi.org/project/agentzero-cli/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Agent Zero CLI Demo](assets/demo.gif)

## Why Agent Zero CLI?

- **Security First** - Every command goes through approval. Dangerous patterns blocked automatically.
- **Local LLM Support** - Run with Ollama, LM Studio - your data never leaves your machine.
- **Multi-Backend** - Switch between Local LLM, OpenRouter, or deterministic mode.
- **Real Tool Execution** - Actually runs shell commands, reads/writes files.
- **TUI + CLI** - Beautiful terminal UI or simple CLI mode.

## Quick Install

```bash
pip install agentzero-cli
```

Then run:
```bash
a0      # TUI mode (recommended)
a0cli   # CLI mode
```

## Backend Configuration

Agent Zero CLI supports multiple backends with automatic fallback:

| Priority | Backend | Data Location | Setup |
|----------|---------|---------------|-------|
| 1 | **Local LLM** | Your machine | `LOCAL_LLM_URL=http://localhost:1234/v1` |
| 2 | Agent Zero API | Your server | `AGENTZERO_API_URL=http://...` |
| 3 | OpenRouter | Cloud | `OPENROUTER_API_KEY=sk-or-...` |
| 4 | Deterministic | Local | No config needed |

### Recommended: Local LLM (Safest)

```bash
# With LM Studio (port 1234)
export LOCAL_LLM_URL=http://localhost:1234/v1

# With Ollama (port 11434)  
export LOCAL_LLM_URL=http://localhost:11434/v1

a0
```

Your prompts **never leave your machine**.

### Alternative: OpenRouter (Cloud)

```bash
export OPENROUTER_API_KEY=sk-or-...
a0
```

## Security Modes

| Mode | Read-only | Write ops | Dangerous |
|------|-----------|-----------|-----------|
| `paranoid` | Confirm | Confirm | BLOCKED |
| `balanced` | Auto-approve | Confirm | BLOCKED |
| `god_mode` | Auto | Auto | BLOCKED |

Dangerous patterns like `rm -rf /`, fork bombs, etc. are **always blocked**.

## Features

- **Security Interceptor** - Blocks dangerous commands, requires approval for writes
- **Risk Analysis** - AI explains command risks before you approve
- **Multi-Model Load Balancing** - Distribute requests across models
- **Live Activity Feed** - AI news during agent thinking
- **Syntax Highlighting** - Beautiful code display
- **Session History** - Persistent conversation context

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | Menu |
| F3 | Mini-game |
| F10 | Quit |
| Enter | Send |
| Shift+Enter | New line |

## Development

```bash
git clone https://github.com/vizi2000/agentzero-cli
cd agentzero-cli
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Roadmap

- [x] TUI Interface (Textual)
- [x] Security interceptor
- [x] Local LLM support (Ollama, LM Studio)
- [x] OpenRouter integration
- [x] Real tool execution
- [x] PyPI package
- [ ] MCP protocol support
- [ ] VS Code extension

## License

MIT License - see [LICENSE](LICENSE)

---

## About

Developed by **Wojciech Wiesner** | [wojciech@theones.io](mailto:wojciech@theones.io)

**[TheOnes](https://theones.io)** - Cutting edge tech powered by Neurodivergent minds

**Neurodivergent?** If you thrive on patterns, hyperfocus, and rapid iteration - let's build together.

- [GitHub](https://github.com/vizi2000/agentzero-cli)
- [AI News Feed](https://feed.theones.io)
- [TheOnes.io](https://theones.io)
