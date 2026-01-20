# AgentZeroCLI - Roadmap do Produkcji

**Cel:** Zamienić demo/mock w pełnoprawnego AI coding agenta jak Claude Code / OpenCode

---

## FAZA 1: Fundament (4-6h)

### 1.1 OpenRouter Backend [KRYTYCZNE]
- [ ] Stwórz `llm_providers/openrouter.py` z prawdziwą integracją
- [ ] Streaming responses (SSE) dla Chain-of-Thought
- [ ] Obsługa wielu modeli (Claude, GPT-4, Llama, etc.)
- [ ] Error handling i retry logic
- [ ] Token counting i cost tracking

```python
# Docelowa struktura
class OpenRouterBackend:
    async def chat(messages, stream=True) -> AsyncGenerator
    async def analyze_risk(command) -> RiskAssessment
    async def execute_tool(tool_call) -> ToolResult
```

### 1.2 Prawdziwe wykonywanie komend [KRYTYCZNE]
- [ ] Sandbox dla shell commands (subprocess z timeout)
- [ ] Walidacja przeciw whitelist/blacklist
- [ ] Capture stdout/stderr w real-time
- [ ] Working directory management
- [ ] Environment isolation

### 1.3 Konfiguracja [WAŻNE]
- [ ] Stwórz `.env.example` z wymaganymi zmiennymi
- [ ] Dodaj `python-dotenv` do requirements
- [ ] Obsługa API keys z env vars
- [ ] Walidacja config przy starcie

---

## FAZA 2: Prosta Instalacja (2-3h)

### 2.1 One-liner install (jak OpenCode)
- [ ] Stwórz `install.sh` script:
```bash
curl -fsSL https://agentzerocli.dev/install | bash
```
- [ ] Homebrew formula: `brew install agentzerocli`
- [ ] PyPI package: `pip install agentzerocli`
- [ ] Automatyczna detekcja OS (macOS, Linux, Windows)

### 2.2 CLI Entry Point
- [ ] Stwórz `__main__.py` dla `python -m agentzerocli`
- [ ] Dodaj `entry_points` w `setup.py`/`pyproject.toml`
- [ ] Komenda `a0` lub `agent0` w PATH

### 2.3 First-run setup
- [ ] Interaktywny wizard: "Enter your OpenRouter API key:"
- [ ] Zapisz config w `~/.config/agentzerocli/`
- [ ] Test connection przy pierwszym uruchomieniu

---

## FAZA 3: Core Features (6-8h)

### 3.1 Tool System
- [ ] File operations: read, write, edit, glob, grep
- [ ] Git integration: status, diff, commit, push
- [ ] Shell execution z approval flow
- [ ] Web fetch dla dokumentacji

### 3.2 Context Management
- [ ] Automatyczne ładowanie CLAUDE.md / AGENTS.md
- [ ] Project detection (package.json, pyproject.toml, etc.)
- [ ] Smart file inclusion w context
- [ ] Token budget management

### 3.3 Memory / Persistence
- [ ] Historia sesji (`.a0/sessions/`)
- [ ] Undo/redo dla zmian w plikach
- [ ] Integracja z `borg-memory` (opcjonalnie)

### 3.4 Security Enhancements
- [ ] Permission system (ask/allow/deny per tool)
- [ ] Audit log wszystkich wykonanych komend
- [ ] Rollback capability

---

## FAZA 4: UX Polish (3-4h)

### 4.1 UI Improvements
- [ ] Syntax highlighting w code blocks
- [ ] Progress indicators dla długich operacji
- [ ] Split-pane: chat + file preview
- [ ] Responsive layout

### 4.2 Keybindings
- [ ] `Ctrl+C` - interrupt current operation
- [ ] `Ctrl+Z` - undo last change
- [ ] `Ctrl+L` - clear chat
- [ ] `Tab` - autocomplete commands
- [ ] `/` commands (jak Discord/Slack)

### 4.3 Themes
- [ ] Dark (default)
- [ ] Light
- [ ] Dracula
- [ ] Nord

---

## FAZA 5: Distribution (2-3h)

### 5.1 Packaging
- [ ] `pyproject.toml` z metadata
- [ ] GitHub Actions dla releases
- [ ] Auto-publish do PyPI
- [ ] Homebrew tap

### 5.2 Documentation
- [ ] README z GIFs/screenshots
- [ ] Quick start guide
- [ ] API reference
- [ ] Configuration reference

### 5.3 Testing
- [ ] Unit tests dla backend
- [ ] Integration tests dla tools
- [ ] E2E tests dla TUI
- [ ] CI pipeline

---

## FAZA 6: Advanced (opcjonalne)

### 6.1 MCP Support
- [ ] MCP client dla external tools
- [ ] Integracja z Context7, Notion, etc.

### 6.2 Multi-agent
- [ ] Sub-agents dla specjalizowanych zadań
- [ ] Agent orchestration

### 6.3 Plugins
- [ ] Plugin system dla custom tools
- [ ] Community plugins repo

---

## Szacowany czas

| Faza | Czas | Priorytet |
|------|------|-----------|
| 1. Fundament | 4-6h | KRYTYCZNE |
| 2. Instalacja | 2-3h | WYSOKIE |
| 3. Core Features | 6-8h | WYSOKIE |
| 4. UX Polish | 3-4h | ŚREDNIE |
| 5. Distribution | 2-3h | ŚREDNIE |
| 6. Advanced | 4-8h | NISKIE |

**MVP (Faza 1-2):** ~8h
**Pełna wersja (Faza 1-5):** ~20h

---

## Quick Start (po implementacji)

```bash
# Instalacja
curl -fsSL https://agentzerocli.dev/install | bash
# lub
pip install agentzerocli

# Konfiguracja
export OPENROUTER_API_KEY="sk-..."

# Uruchomienie
a0
# lub
agent0

# W projekcie
cd ~/Projects/myapp
a0
```

---

## Stack technologiczny

- **UI:** Textual (Python TUI)
- **LLM:** OpenRouter (multi-model)
- **Config:** YAML + dotenv
- **Packaging:** PyPI + Homebrew
- **Testing:** pytest + pytest-asyncio

---

*Utworzono: 2026-01-20*
*Projekt: AgentZeroCLI → Borg.tools*
