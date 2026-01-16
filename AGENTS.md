# AGENTS.md — Agent Zero CLI

## Purpose

This file orients agentic coding assistants working in this repo. Keep edits small, follow existing conventions, and validate with tests/lint.

## Repo Overview

- Python 3.10+ CLI/TUI client for Agent Zero
- Entry points: `a0cli` (CLI) and `a0tui` (TUI)
- Core modules: `backend.py`, `cli/`, `ui/`, `observer/`, `llm_providers/`
- Tests live in `tests/`

## Quick Start (Dev)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Build / Run Commands

- Run CLI: `a0cli` or `python -m cli`
- Run TUI: `a0tui` or `python -m main_new`
- Package build (optional): `python -m build`

## Lint / Format

- Lint: `ruff check .`
- Format check: `black --check .`
- Auto-format: `black .`
- Optional autofix: `ruff check . --fix`

## Tests

- Run full suite: `pytest tests/`
- Run with coverage: `pytest tests/ --cov=. --cov-report=html`
- Run a single file: `pytest tests/test_backend_context.py`
- Run a single test: `pytest tests/test_backend_context.py::TestContextBuilder::test_preview_redaction`
- Run by keyword: `pytest -k "context"`
- E2E (mock server): `scripts/run_e2e.sh`

## Cursor / Copilot Rules

- No `.cursor/rules`, `.cursorrules`, or `.github/copilot-instructions.md` found in this repo.

## Code Style & Conventions

### Python & Typing

- Target Python 3.10+.
- Use type hints for function signatures and public APIs.
- Prefer `Optional[T]` or `T | None` over implicit `None`.
- Keep functions small and focused; avoid side effects in helpers.

### Formatting

- Formatting is enforced by Black.
- Line length is 100 characters (`[tool.black]` and `[tool.ruff]`).
- Do not hand-format to a different width.

### Imports

- Follow Ruff import sorting (isort-style).
- Group imports in this order: standard library, third-party, local.
- Keep imports explicit; avoid `from x import *`.

### Naming

- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Async functions: suffix with `_async` only if it clarifies intent.

### Error Handling

- Catch specific exceptions; avoid bare `except`.
- Log with `logging.getLogger("agentzero.<module>")`.
- Return safe, user-facing messages rather than raw stack traces.
- Preserve original exceptions where helpful for debugging.

### Async & IO

- Prefer `async`/`await` with `aiohttp` where used.
- Use timeouts and close sessions with context managers.
- Avoid blocking calls in async paths; use `asyncio.to_thread` if needed.

### Configuration & Secrets

- Config lives in `config.yaml` / `config.example.yaml`.
- Environment variables are prefixed with `AGENTZERO_`.
- Never commit secrets or real API keys.

### Logging & Output

- Use `logging` instead of `print`.
- Keep user-facing messages consistent with existing CLI/TUI output styles.

### Tests

- Use pytest and pytest-asyncio (`asyncio_mode = auto`).
- Add tests for new behaviors; keep them deterministic.
- Prefer unit tests in `tests/` over ad-hoc scripts.

## Repo Layout

- `backend.py` — Agent Zero client + context builder
- `cli/` — CLI interface and slash commands
- `ui/` — Textual-based TUI
- `observer/` — Tool routing and observer logic
- `llm_providers/` — LLM integration adapters
- `docs/` — Project docs and specs

## Change Hygiene

- Keep diffs minimal and scoped to the task.
- Do not add new dependencies without explicit approval.
- Update docs when behavior or config changes.
- Prefer tests + lint before requesting review.

## Security Notes

- Redact or exclude sensitive data in logs and previews.
- Be careful with filesystem operations; avoid destructive defaults.

## How to Add New Tests

1. Place tests in `tests/` using `test_*.py` naming.
2. Name test classes `TestSomething` and test functions `test_something`.
3. For async tests, use `async def` + pytest-asyncio.

## Definition of Done

- Lint and format checks pass.
- Relevant tests pass (or clearly noted).
- No secrets added to git.
- Documentation updated when needed.
