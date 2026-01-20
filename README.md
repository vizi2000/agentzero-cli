# Agent Zero CLI

> AI coding agent with security interceptor - your prompts, your machine, your control.

[![PyPI version](https://badge.fury.io/py/agentzero-cli.svg)](https://pypi.org/project/agentzero-cli/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Quick Demo

![Agent Zero CLI Demo](assets/demo.gif)

## Quick Install

```bash
pip install agentzero-cli
a0
```

## Why Agent Zero CLI?

- **Security First** - Every command goes through approval. Dangerous patterns blocked automatically.
- **Local LLM Support** - Run with Ollama, LM Studio - your data never leaves your machine.
- **Multi-Backend** - Switch between Local LLM, OpenRouter, or deterministic mode.
- **Real Tool Execution** - Actually runs shell commands, reads/writes files.

---

## Features in Action

### Security Interceptor

Dangerous commands like `rm -rf /` and fork bombs are **automatically blocked**:

![Security Demo](assets/demo_security.gif)

### Code Generation

Generate code with syntax highlighting and file save approval:

![Code Generation Demo](assets/demo_codegen.gif)

### Risk Explanation

Press `[E]` to ask AI to explain the risk before approving:

![Risk Explanation Demo](assets/demo_risk.gif)

### Model Switching (LM Studio)

Use any model from your local LM Studio server:

![Model Switch Demo](assets/demo_model_switch.gif)

### Multi-Backend Support

Automatic fallback chain with Local LLM as the safest option:

![Backends Demo](assets/demo_backends.gif)

---

## Backend Configuration

| Priority | Backend | Data Location | Setup |
|----------|---------|---------------|-------|
| 1 | **Local LLM** | Your machine | `LOCAL_LLM_URL=http://localhost:1234/v1` |
| 2 | Agent Zero API | Your server | `AGENTZERO_API_URL=http://...` |
| 3 | OpenRouter | Cloud | `OPENROUTER_API_KEY=sk-or-...` |
| 4 | Deterministic | Local | No config needed |

### Local LLM Setup (Recommended)

```bash
# LM Studio
export LOCAL_LLM_URL=http://localhost:1234/v1
export LOCAL_LLM_MODEL=mistralai/ministral-3-3b  # optional

# Ollama
export LOCAL_LLM_URL=http://localhost:11434/v1
export LOCAL_LLM_MODEL=llama3.2:3b

# Remote LM Studio (e.g., on another machine)
export LOCAL_LLM_URL=http://192.168.1.100:1234/v1

a0
```

Your prompts **never leave your network**.

### OpenRouter (Cloud)

```bash
export OPENROUTER_API_KEY=sk-or-...
a0
```

---

## Security Modes

| Mode | Read-only | Write ops | Dangerous |
|------|-----------|-----------|-----------|
| `paranoid` | Confirm | Confirm | BLOCKED |
| `balanced` | Auto-approve | Confirm | BLOCKED |
| `god_mode` | Auto | Auto | BLOCKED |

Dangerous patterns are **always blocked**, regardless of mode:
- `rm -rf /`, `rm -rf ~`
- Fork bombs `:(){ :|:& };:`
- `mkfs.*`, `dd if=/dev/`
- Download and execute (`curl | sh`)

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | Menu |
| F3 | Mini-game |
| F10 | Quit |
| Enter | Send |
| Shift+Enter | New line |

---

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

---

## Roadmap

- [x] TUI Interface (Textual)
- [x] Security interceptor with blocklist
- [x] Local LLM support (Ollama, LM Studio)
- [x] OpenRouter integration
- [x] Real tool execution
- [x] Risk explanation
- [x] PyPI package
- [ ] MCP protocol support
- [ ] VS Code extension

---

## License

MIT License - see [LICENSE](LICENSE)

---

## About

Developed by **Wojciech Wiesner** | [wojciech@theones.io](mailto:wojciech@theones.io)

**[TheOnes](https://theones.io)** - Cutting edge tech powered by Neurodivergent minds

**Neurodivergent?** If you thrive on patterns, hyperfocus, and rapid iteration - let's build together.

[![GitHub](https://img.shields.io/badge/GitHub-vizi2000-black?logo=github)](https://github.com/vizi2000/agentzero-cli)
[![Website](https://img.shields.io/badge/Web-theones.io-blue)](https://theones.io)
[![News](https://img.shields.io/badge/AI_News-feed.theones.io-orange)](https://feed.theones.io)
