# AgentZeroCLI - Project Rules

## Project Overview
TUI-based AI coding agent with security interceptor and mini-game.
Goal: Production-ready alternative to Claude Code / OpenCode.

## Tech Stack
- **UI:** Textual (Python TUI framework)
- **LLM:** OpenRouter API (multi-model support)
- **Config:** YAML + python-dotenv
- **Testing:** pytest + pytest-asyncio

## Architecture

```
agentzerocli/
├── main.py              # TUI application (Textual)
├── backend.py           # LLM backend (TO REPLACE)
├── llm_providers/       # OpenRouter, local models
├── tools/               # File ops, git, shell
├── ui/                  # Refactored UI components
└── config.yaml          # User configuration
```

## Current Status
- UI: Working (Textual TUI)
- Backend: MOCKED (needs OpenRouter integration)
- Tools: NOT IMPLEMENTED
- Tests: NONE

## Coding Standards
- Max 300 lines per file
- Type hints required
- Async/await for all I/O
- Error handling with custom exceptions

## Commands
```bash
# Dev
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Test (once implemented)
pytest tests/
```

## Priority Tasks
1. Replace MockAgentBackend with OpenRouterBackend
2. Implement real tool execution
3. Add .env support for API keys
4. Create one-liner installer

## Security Rules
- NEVER execute commands without user approval (except whitelist)
- Log all tool executions
- Validate all file paths (no path traversal)
- Timeout on all shell commands

## File Size Limits
- main.py is 340 lines - needs refactoring to ui/ modules
- Target: <200 lines per file after refactor
