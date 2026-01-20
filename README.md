# Agent Zero CLI

> TUI-based AI coding agent with security interceptor

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **AI-Powered Coding Assistant** - Chat interface for code tasks
- **Security Interceptor** - Blocks dangerous commands (rm -rf, etc.)
- **Risk Analysis** - AI explains command risks before execution
- **Multi-Model Support** - OpenRouter integration (Claude, GPT-4, Llama)
- **Mini-Game** - "Agent ZUSA: Poland Mission" (F1 to play)

## Quick Start

### Installation

```bash
# Option 1: pip (recommended)
pip install agentzerocli

# Option 2: From source
git clone https://github.com/borg-tools/agentzerocli
cd agentzerocli
pip install -e .
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
# Start the agent
a0

# Or with Python
python -m agentzerocli
```

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

## Mini-Game: Agent ZUSA

Press **F1** to play "Agent ZUSA: TheOnes" (Polish Mission)
- Play as Agent0 (bald with beard `[🧔]`)
- Teleport between Polish cities
- Fight EvilAGI virus (costs Tokens)
- Stake Tokens in secure cities

## Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python main.py

# Test
pytest tests/
```

## Roadmap

- [x] TUI Interface (Textual)
- [x] Security interceptor
- [x] Mini-game
- [ ] OpenRouter integration
- [ ] Real tool execution
- [ ] One-liner installer
- [ ] MCP support

See [TODO.md](TODO.md) for full roadmap.

## License

MIT License

## Credits

Created by **The Collective Borg.tools**
