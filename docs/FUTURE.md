# Roadmap: State-of-the-Art polish

This file captures the concrete actions (with acceptance) that remain to elevate Agent Zero CLI / Launcher to a best-in-class, release-ready experience.

## 1. Testing + CI
### Goal
Automate functional verification so every change can be validated before publish.
### Steps
1. Add `tests/` with:
   - `test_backend_context.py` (mock config, verify context signature, redaction, `context_id` handling).
   - `test_tool_flow.py` (use `MockAgentBackend`+`RemoteAgentBackend` stub to assert tool approval/rejection pipeline).
   - `test_cli_commands.py` (simulate slash command parsing and whitelist logic).
   - Snapshot tests for `docs/README.md` output? optional.
2. Add `tests/conftest.py` for fixtures (temp workspace, sandbox config).
3. Create GitHub Actions workflow `ci.yml`:
   - `setup-python` (3.10+), install requirements inside virtualenv.
   - `lint` job (flake8 or optional `ruff`).
   - `test` job running `pytest tests/ --maxfail=1`.
4. Ensure CI protects main branch with status checks (document in README).
### Acceptance
- `pytest` exits 0 locally and in CI.
- Workflow fails if formatting/test coverage regress.

## 2. E2E harness + mock server
### Goal
Validate streaming/int/ tool result round-trips before hitting production API.
### Steps
1. Create `tests/mock_api.py`: aiohttp server mimicking Agent Zero responses (SSE/JSONL, tool requests etc.).
2. Add `tests/e2e_test.py` that:
   - Starts mock server via subprocess/`pytest-asyncio`.
   - Point CLI/TUI backend to mock API (`AGENTZERO_API_URL` override).
   - Sends message, approves, rejects, ensures `context_id` flows.
3. Document how to run e2e (`scripts/run_e2e.sh`), optionally gating on `E2E=true`.
4. Hook `tests/e2e_test.py` into CI (flagged optional, run nightly or manual).
### Acceptance
- Mock server emits SSE/JSONL and tool_request events.
- Test script confirms UI/backend handle reject + `tool_result`.

## 3. Packaging + Distribution
### Goal
Ship CLI as installable package + portable launcher.
### Steps
1. Add `pyproject.toml` (poetry/PEP 621) describing package metadata, dependencies, entry points (`agentzero-cli`, `agentzero-launcher`).
2. Create `setup.py` optional stub for compatibility.
3. Provide shell completions (`bash`, `zsh`) referencing slash commands.
4. Publish on PyPI/`pip install agentzero-cli`.
5. Add instructions for `pip install .` + `./a0` on README.
### Acceptance
- `pip install .` creates working entry points.
- `./a0` uses installed interpreter and respects new CLI.

## 4. Documentation polish
### Goal
Make everything discoverable and approachable.
### Steps
1. Expand docs:
   - `docs/ARCHITECTURE.md` (sequence diagram: prompt -> context -> tool -> result).
   - `docs/FAQ.md` ( security, context, CLI vs TUI, launcher env).
   - `docs/CONTRIBUTING.md` (branching, tests, release, issue labels).
2. Add inline docstrings (backend context builder, CLI approvals) referencing docs.
3. Publish `README` badges (build, PyPI, license).
4. Include `docs/CHANGELOG.md` template for future releases.
### Acceptance
- Docs folder contains new topics and is referenced from README.
- Contributors have clear “how to contribute” steps.

## 5. Observability + UX
### Goal
Understand agent activity and make UI more resilient.
### Steps
1. Add verbose/debug flag (`--debug`, `DEBUG=true`) that enables detailed logging (backend connection info, tool payloads) with `logging` module.
2. Log tool approvals/rejections to `logs/agentzero.log` when `DEBUG` enabled.
3. Implement chat session persistence + ability to export conversation (`docs/export` explanation).
4. Add CLI auto-completion script referencing `CLISlashCommands`.
5. Provide `uploads/` cleanup script to avoid stale copies.
### Acceptance
- Debug flag toggles verbose logs (note in docs).
- CLI completion script works (`source completion.sh`).

## 6. Security review
### Goal
Ensure there are no silent leaks/resets.
### Steps
1. Scan workspace for potential leaks (pyproject, README) and extend `backend.SENSITIVE_FILES`.
2. Add `scripts/rotate_api_key.sh` template to remind users to rotate keys.
3. Document `config.local.yaml` override vs env var for secrets.
### Acceptance
- README states secrets must be env vars.
- Scripts/documentation exist for rotating keys.

## Summary
These steps cover automation, quality, packaging, documentation, observability, and governance. Implement them incrementally (tests → packaging → docs → UX) to reach a state-of-the-art release. Use this file as a checklist when opening PRs/issues for each area.
