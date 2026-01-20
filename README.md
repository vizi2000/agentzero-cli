# Agent Zero CLI

> TUI-based AI coding agent with security interceptor and live activity feed

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **AI-Powered Coding Assistant** - Chat interface for code tasks
- **Security Interceptor** - Blocks dangerous commands (rm -rf, etc.)
- **Risk Analysis** - AI explains command risks before execution
- **Multi-Model Support** - OpenRouter integration with load balancing
- **Live Activity Feed** - AI news + project insights during thinking
- **Mini-Game** - "Agent ZUSA: Poland Mission" (F3 to play)

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/vizi2000/agentzero-cli
cd agentzero-cli

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY="sk-or-..."

# Or create .env file
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

### Usage

```bash
# Run TUI
python main.py

# Or CLI mode
python cli.py
```

## Activity Feed

During agent thinking, the activity panel shows:

- **AI News** - Latest from Anthropic, OpenAI, Google AI, Hugging Face
- **Project Insights** - Code suggestions, security tips, refactoring hints
- **Best Practices** - AI/LLM development tips

News powered by [feed.theones.io](https://feed.theones.io)

## Security Modes

| Mode | Description |
|------|-------------|
| `paranoid` | Ask approval for everything |
| `balanced` | Auto-approve reads, ask for writes |
| `god_mode` | Auto-approve everything (dangerous!) |

Configure in `config.yaml`:

```yaml
security:
  mode: "balanced"
  whitelist:
    - "ls"
    - "cat"
    - "git status"
  blacklist_patterns:
    - "rm -rf"
    - "shutdown"
```

## OpenRouter Integration

Load-balanced between free models:
- `mistralai/devstral-2512:free`
- `xiaomi/mimo-v2-flash:free`
- `qwen/qwen3-coder:free`

Falls back to mock mode if no API key is set.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | Menu |
| F3 | Mini-game |
| F10 | Quit |
| Enter | Send message |
| Shift+Enter | New line |

## Development

```bash
# Run tests
pytest tests/ -v

# Check syntax
python -m py_compile main.py

# Run with debug
AGENT_DEBUG=true python main.py
```

## Project Structure

```
agentzerocli/
├── main.py              # TUI entry point
├── cli.py               # CLI entry point
├── backend.py           # Backend factory
├── llm_providers/
│   └── openrouter.py    # OpenRouter integration
├── ui/
│   ├── app.py           # Main TUI application
│   ├── insights.py      # News + project insights
│   └── screens/         # Modal screens
├── cli/
│   └── news.py          # CLI news display
├── feed.theones.io/     # News feed infrastructure
│   └── collector/       # RSS collector + AI rewriter
└── tests/
    └── test_openrouter.py
```

## Roadmap

- [x] TUI Interface (Textual)
- [x] Security interceptor
- [x] OpenRouter integration (load balancing)
- [x] Live activity feed (news + insights)
- [x] Mini-game
- [ ] Real tool execution
- [ ] MCP support
- [ ] One-liner installer

## License

MIT License

## Links

- [GitHub](https://github.com/vizi2000/agentzero-cli)
- [AI News Feed](https://feed.theones.io)
- [TheOnes.io](https://theones.io)

---

Created by **The Collective Borg.tools**
