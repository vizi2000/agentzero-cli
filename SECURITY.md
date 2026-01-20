# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Agent Zero CLI, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email: **wojciech@theones.io**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

## Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity (critical: ASAP, high: 14 days, medium: 30 days)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |

## Security Best Practices

When using Agent Zero CLI:

1. **Never commit secrets** - Use environment variables or `.env` files
2. **Use appropriate security mode** - Start with `paranoid` mode until you trust the setup
3. **Review tool requests** - Always check what the agent wants to execute
4. **Keep dependencies updated** - Run `pip install --upgrade agentzero-cli` regularly
5. **Use whitelist/blacklist** - Configure shell command restrictions in `config.yaml`

## Known Security Features

- **Three security modes**: paranoid (approve all), balanced (auto-approve reads), god_mode (auto-approve all)
- **Context redaction**: API keys and secrets are masked in previews
- **Sensitive file exclusion**: `.env`, `config.yaml`, credentials files are excluded from context
- **Shell command filtering**: Whitelist/blacklist for shell commands
- **Symlink protection**: Prevents traversal outside workspace
