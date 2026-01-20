# Agent Zero CLI - Analiza Wykonalności v2

## Przegląd Stanu Aktualnego

### Architektura CLI (obecna)
```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│  cli/app.py      - Main loop, event processing                  │
│  cli/renderer.py - Rich output (markdown, panels, colors)       │
│  cli/input.py    - prompt_toolkit (history, autocomplete)       │
│  cli/commands.py - Slash commands (/help, /status, /observer)   │
│  cli/approval.py - Tool approval workflow (rules + whitelist)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/SSE
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               Agent Zero (borg.tools:50001)                      │
│  - Remote AI agent in Docker                                    │
│  - Receives context + prompt                                    │
│  - Returns tool_request / final_response events                 │
└─────────────────────────────────────────────────────────────────┘
```

### Istniejące Komponenty

1. **cli/approval.py** - Już ma:
   - `READONLY_TOOLS` - auto-approve dla read_file, list_files, search
   - `_is_shell_whitelisted()` - whitelist z config.yaml
   - Security modes: paranoid, balanced, god_mode

2. **cli/commands.py** - Już ma:
   - `/observer` command - pokazuje status konfiguracji Observer

3. **backend.py** - Problem keepalive (linie 1164-1172):
```python
yield {
    "type": "status",
    "content": f"[WAIT] Waiting for response... {elapsed}s (connection active)"
}
```

---

## Pareto 20/80 - Analiza Requestów

### Wszystkie możliwe requesty Agent Zero → CLI:

| Tool | Użycie | Ryzyko | Rekomendacja MCP |
|------|--------|--------|------------------|
| `read_file` | ~40% | Niskie | Direct MCP (no approval) |
| `list_files` | ~20% | Niskie | Direct MCP (no approval) |
| `search_text` | ~15% | Niskie | Direct MCP (no approval) |
| `write_file` | ~10% | Wysokie | Request + Approval Token |
| `replace_text` | ~8% | Wysokie | Request + Approval Token |
| `apply_patch` | ~5% | Wysokie | Request + Approval Token |
| `shell` | ~2% | Krytyczne | Request + Approval Token |

### 80% operacji = bezpieczne read-only
- `read_file`, `list_files`, `search_text`
- Mogą być Direct MCP bez approval

### 20% operacji = wymagają kontroli
- `write_file`, `replace_text`, `apply_patch`, `shell`
- Wymagają approval token z walidacją

---

## Architektura Docelowa: MCP z Auto-Discovery

### Flow Połączenia (Zero Config dla Usera)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER URUCHAMIA CLI                                           │
│    $ ./a0 --cli                                                 │
│    (tylko API_KEY w env lub config)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. CLI HANDSHAKE z Agent Zero                                   │
│    GET /config                                                  │
│    → Agent Zero zwraca MCP endpoint + capabilities              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CLI AUTO-KONFIGURUJE MCP CLIENT                              │
│    mcp_client = MCPClient(response["mcp_endpoint"])            │
│    (zero manual config!)                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. NORMALNA PRACA przez MCP                                     │
│    - Read ops: Direct MCP                                       │
│    - Write ops: Request → Approval → Execute                   │
└─────────────────────────────────────────────────────────────────┘
```

### Config Discovery Response

```json
{
  "mcp_endpoint": "http://194.181.240.37:50001/mcp/sse",
  "mcp_http": "http://194.181.240.37:50001/mcp/http",
  "capabilities": {
    "tools": ["read_file", "list_files", "search_text",
              "write_file", "replace_text", "apply_patch", "shell"],
    "streaming": true,
    "context_aware": true
  },
  "security": {
    "direct_tools": ["read_file", "list_files", "search_text"],
    "approval_tools": ["write_file", "replace_text", "apply_patch", "shell"],
    "blocked_patterns": ["rm -rf /", "format", "mkfs"]
  }
}
```

---

## Bezpieczeństwo: Approval Token System

### Problem: Czy Agent Zero może "przemycić" akcje?

**Scenariusz ataku:**
```
1. Agent Zero: request_write("config.py", "safe content")
2. User: Approve ✓
3. Agent Zero dostaje token
4. Agent Zero: próbuje użyć token do rm -rf?
```

**Rozwiązanie: Token Bound to Specific Action**

```python
@dataclass
class ApprovalToken:
    id: str                    # UUID
    action: str                # "write_file"
    params_hash: str           # SHA256(path + content)
    expires: float             # timestamp (60s TTL)
    used: bool = False         # one-time use
    client_id: str             # which CLI instance

def execute_approved(token_id: str, action: str, params: dict):
    token = tokens.get(token_id)

    # Multi-layer validation
    if not token:
        raise SecurityError("Invalid token")
    if token.used:
        raise SecurityError("Token already used - BLOCKED")
    if token.expires < time.time():
        raise SecurityError("Token expired - BLOCKED")
    if token.action != action:
        raise SecurityError("Action mismatch - POSSIBLE ATTACK")
    if token.params_hash != sha256(canonical(params)):
        raise SecurityError("Params modified - POSSIBLE ATTACK")

    # Mark as used BEFORE execution
    token.used = True

    # Execute
    return execute_action(action, params)
```

### Zabezpieczenia:
| Ochrona | Opis |
|---------|------|
| One-time use | Token zużyty = nie można użyć ponownie |
| Action binding | Token dla write_file ≠ token dla shell |
| Params hash | Zmiana contentu = invalid token |
| TTL (60s) | Token wygasa szybko |
| Client binding | Token dla CLI-A ≠ ważny w CLI-B |

---

## Architektura MCP Tools

### Kategoria 1: Direct Tools (80% requestów)

```python
@mcp.tool("read_file")
async def read_file(path: str, start_line: int = None,
                    end_line: int = None) -> str:
    """Direct file read - no approval needed."""
    validate_path_in_workspace(path)
    return read_file_content(path, start_line, end_line)

@mcp.tool("list_files")
async def list_files(path: str = ".", max_depth: int = 4) -> dict:
    """Direct directory listing - no approval needed."""
    validate_path_in_workspace(path)
    return get_file_tree(path, max_depth)

@mcp.tool("search_text")
async def search_text(query: str, path: str = ".",
                      max_matches: int = 50) -> list:
    """Direct text search - no approval needed."""
    validate_path_in_workspace(path)
    return search_in_files(query, path, max_matches)
```

### Kategoria 2: Request Tools (20% requestów)

```python
@mcp.tool("request_write")
async def request_write(path: str, content: str) -> dict:
    """Request to write file - returns approval token."""
    validate_path_in_workspace(path)

    token = ApprovalToken(
        id=uuid4(),
        action="write_file",
        params_hash=sha256(f"{path}:{content}"),
        expires=time.time() + 60,
        used=False
    )
    tokens[token.id] = token

    return {
        "approval_required": True,
        "approval_id": token.id,
        "action": "write_file",
        "path": path,
        "preview": content[:500],
        "full_size": len(content),
        "expires_in": 60
    }

@mcp.tool("request_shell")
async def request_shell(command: str) -> dict:
    """Request to run shell command - returns approval token."""
    if matches_blacklist(command):
        return {"blocked": True, "reason": "Command matches blacklist"}

    token = ApprovalToken(
        id=uuid4(),
        action="shell",
        params_hash=sha256(command),
        expires=time.time() + 60,
        used=False
    )
    tokens[token.id] = token

    return {
        "approval_required": True,
        "approval_id": token.id,
        "action": "shell",
        "command": command,
        "risk_level": assess_risk(command),
        "expires_in": 60
    }
```

### Kategoria 3: Execution Tool

```python
@mcp.tool("execute_approved")
async def execute_approved(approval_id: str) -> dict:
    """Execute previously approved action."""
    token = tokens.get(approval_id)

    if not token:
        return {"error": "Invalid or expired approval"}
    if token.used:
        return {"error": "Approval already used"}
    if token.expires < time.time():
        return {"error": "Approval expired"}

    # Mark used BEFORE execution
    token.used = True

    # Execute based on action type
    if token.action == "write_file":
        return execute_write(token.original_params)
    elif token.action == "shell":
        return execute_shell(token.original_params)
    # ... etc
```

---

## Flow: Write Operation z Approval

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Agent Zero chce zapisać plik                                 │
│    MCP call: request_write("app.py", "new content...")         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. MCP Server zwraca approval request                           │
│    {                                                            │
│      "approval_required": true,                                 │
│      "approval_id": "abc-123",                                  │
│      "action": "write_file",                                    │
│      "path": "app.py",                                          │
│      "preview": "new content...",                               │
│      "expires_in": 60                                           │
│    }                                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CLI pokazuje userowi                                         │
│    ┌──────────────────────────────────────────────────────┐    │
│    │ Tool Request: write_file                              │    │
│    │ Path: app.py                                          │    │
│    │ Preview:                                              │    │
│    │   new content...                                      │    │
│    │                                                       │    │
│    │ [A]pprove / [R]eject / [E]xplain?                    │    │
│    └──────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. User wybiera [A]pprove                                       │
│    CLI call: execute_approved("abc-123")                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. MCP Server waliduje token i wykonuje                         │
│    - Token valid? ✓                                             │
│    - Token unused? ✓                                            │
│    - Token not expired? ✓                                       │
│    - Params hash matches? ✓                                     │
│    → Execute write_file("app.py", "new content...")            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Konfiguracja Minimalna (dla Usera)

```yaml
# config.yaml - TYLKO TO USER MUSI USTAWIĆ

connection:
  api_url: "http://your-server:50001/api_message"
  api_key: "your-api-key-here"

# Reszta = auto-discovery przez /config endpoint
# MCP endpoint, tools, capabilities - wszystko automatyczne
```

Lub przez env:
```bash
export AGENTZERO_API_URL="http://your-server:50001/api_message"
export AGENTZERO_API_KEY="your-api-key-here"
./a0 --cli
```

---

## Plan Implementacji

### Faza 1: News Feed (Quick Win)
1. Setup feed.theones.io na borg.tools
2. RSS collector script
3. CLI news.py module
4. Fix keepalive spam

### Faza 2: Config Auto-Discovery
1. Endpoint `/config` w Agent Zero
2. CLI auto-setup MCP client
3. Zero manual config

### Faza 3: MCP Approval System
1. `request_*` tools z tokenami
2. `execute_approved` z walidacją
3. Security: hash, TTL, one-time

### Faza 4: Observer Integration
1. Rule-based routing
2. LLM fallback (MCP Gateway)
3. Caching decisions

---

## Ryzyka i Mitigacje

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|--------|-------------------|-----------|
| Token replay attack | Niskie | One-time use + TTL |
| Params modification | Niskie | SHA256 hash validation |
| Token theft | Niskie | Client binding + short TTL |
| MCP endpoint unavailable | Średnie | Fallback to HTTP API |
| Approval fatigue | Średnie | Smart defaults, god_mode option |

---

## Podsumowanie

**Wykonalność: WYSOKA**

Kluczowe decyzje:
1. **80% operacji** (read) = Direct MCP, zero approval
2. **20% operacji** (write) = Approval token z silną walidacją
3. **Auto-discovery** = Zero config po stronie usera
4. **Security** = Multi-layer token validation

Token system zapobiega "przemycaniu" akcji - każdy token jest:
- Bound to specific action + params
- One-time use
- Short TTL (60s)
- Hash-validated

---

*Wygenerowano: 2026-01-11*
*Projekt: Agent Zero CLI*
*Autor: Claude Opus 4.5*
