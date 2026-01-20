# Security Architecture

Agent Zero CLI treats security as a core feature, not an afterthought.

## Security Flow (ALL Backends)

```
User Input --> LLM Backend --> tool_request --> Security Interceptor --> User Approval --> Execute
                  |                                     |
                  |                              [BLOCKED if dangerous]
                  v
         [thinking/response]
```

**Critical**: The security interceptor is NEVER bypassed, regardless of which backend you use. All tool requests go through the same approval flow.

## Backend Selection by Security

| Priority | Backend | Data Location | Security Level |
|----------|---------|---------------|----------------|
| 1 | Local LLM | Your machine | SAFEST - data never leaves |
| 2 | Agent Zero API | Your server | Safe - your infrastructure |
| 3 | OpenRouter | Cloud | Standard - data sent to API |
| 4 | Deterministic | Local | SAFEST - no LLM at all |

### Why Local LLM is SAFEST

When using Local LLM (Ollama, LM Studio, LocalAI):
- Your prompts NEVER leave your network
- No data sent to external servers
- Works completely offline
- Full control over the model

```bash
# Recommended secure setup
LOCAL_LLM_URL=http://localhost:1234/v1  # or your LM Studio IP
```

## Security Modes

| Mode | Read-only | Write ops | Dangerous |
|------|-----------|-----------|-----------|
| `paranoid` | Confirm | Confirm | BLOCKED |
| `balanced` | Auto-approve | Confirm | BLOCKED |
| `god_mode` | Auto-approve | Auto-approve | BLOCKED |

Set via: `AGENT_SECURITY_MODE=balanced`

## Blocked Commands (Always)

These patterns are blocked regardless of security mode:

```python
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    ":(){ :|:& };:",  # fork bomb
    "mkfs.",
    "dd if=/dev/",
    "> /dev/sda",
    "chmod -R 777 /",
    "wget.*|.*sh",    # download and execute
    "curl.*|.*sh",    # download and execute
]
```

## Command Categories

### Read-only (auto-approved in balanced mode)
```
ls, cat, head, tail, grep, find, pwd, echo
git status, git log, git diff, git branch
python --version, pip list
```

### Write operations (require confirmation)
```
rm, rmdir, mv, cp, mkdir, touch
chmod, chown, ln
git push, git commit, git reset
pip install, npm install
```

## Tool Approval Screen

When a tool request needs approval, you'll see:

```
+------------------------------------------+
| TOOL REQUEST                             |
+------------------------------------------+
| Command: rm -rf ./old_backups            |
| Reason:  Clean up old backup files       |
| Risk:    MEDIUM - deletes files          |
+------------------------------------------+
| [A]pprove  [D]eny  [E]xplain risk        |
+------------------------------------------+
```

Press:
- `A` - Execute the command
- `D` - Deny and skip
- `E` - Ask LLM to explain the risk

## Context Redaction

Sensitive data is automatically redacted:

- Keys: `api_key`, `secret`, `password`, `token`
- Patterns: Custom regex via `context.redact_patterns`
- Files: `.env`, `config.yaml` excluded by default

## Best Practices

1. **Use Local LLM** for sensitive codebases
2. **Keep `balanced` mode** for daily use
3. **Never use `god_mode`** in production
4. **Review tool requests** before approval
5. **Use environment variables** for secrets
6. **Keep secrets out of workspace**

## Reporting Security Issues

Found a vulnerability? Please report responsibly:
- Email: security@agentzero.dev
- GitHub: Private security advisory
