# Contributing to Agent Zero CLI

First off, thank you for considering contributing to Agent Zero CLI! It's people like you that make this project better.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Describe the behavior you observed and what you expected**
- **Include your Python version and OS**
- **Include relevant config (redact any API keys!)**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. Ensure the test suite passes
4. Make sure your code follows the project style (see below)
5. Write a clear PR description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/AgentZeroCLI.git
cd AgentZeroCLI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check .
black --check .
```

## Code Style

- **Python 3.10+** is required
- Use **type hints** for function signatures
- Follow **PEP 8** conventions
- Maximum line length: **100 characters**
- Use **black** for formatting
- Use **ruff** for linting

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests when relevant

Example:
```
feat: Add custom theme support

- Allow users to define themes in config.yaml
- Add theme validation on load
- Update docs with theme format

Fixes #42
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring

## Project Structure

```
AgentZeroCLI/
├── backend.py          # HTTP API client, context builder
├── cli/                # CLI interface (non-TUI)
│   ├── app.py          # Main CLI application
│   ├── commands.py     # Slash commands
│   ├── input.py        # Input handling
│   └── renderer.py     # Output rendering
├── ui/                 # TUI interface (Textual)
│   ├── app.py          # Main TUI application
│   ├── chat.py         # Chat widget
│   ├── screens.py      # Screen definitions
│   └── themes.py       # Theme definitions
├── llm_providers/      # LLM integrations
├── observer/           # Workspace monitoring
├── tests/              # Test suite
└── docs/               # Documentation
```

## Testing

- Write tests for new features
- Ensure existing tests pass before submitting PR
- Aim for meaningful coverage, not 100%

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_backend_context.py
```

## Security

- **Never commit API keys or secrets**
- Use `.env` or environment variables for sensitive data
- Report security vulnerabilities via our [Security Policy](SECURITY.md)

## Questions?

Feel free to open an issue with the `question` label or reach out to the maintainers.

---

Thank you for contributing!
