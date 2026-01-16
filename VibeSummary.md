# VibeSummary: AgentZeroCLI

Updated: 2025-03-08
Project Path: /Users/wojciechwiesner/ai/AgentZeroCLI
Languages: python

---

## Project Essence

AgentZeroCLI is a local TUI operator for a remote Agent Zero server. It focuses on safe execution (tool approval), rich context building, and live visibility of what the agent is doing.

---

## What it does
- Connects to Agent Zero over HTTP API (streaming supported)
- Builds and sends workspace context (tree, previews, git)
- Shows live feed of status/thinking/tool events
- Enforces tool approval with configurable security modes
- Supports projects, agent profiles, and UI themes

---

## Current Stage
Beta. Feature-complete for local usage, not packaged for distribution.

---

## Documentation Status
- README is updated and includes setup, usage, config, and troubleshooting
- Config defaults live in config.yaml

---

## Gaps / Next steps
- Add LICENSE
- Add CI + automated tests
- Add packaging (pipx/pyproject)
- Document server API contract and event schema
