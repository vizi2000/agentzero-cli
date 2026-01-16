# Security Notes

## Principles
- Human-in-the-loop for all non-read-only tools by default.
- Tools are limited to `workspace_root` with path traversal protection.
- Shell execution is off by default (`allow_shell=false`).

## Security modes
- `paranoid`: user confirmation required for every tool.
- `balanced`: auto-approve read-only tools and whitelisted shell commands.
- `god_mode`: auto-approve everything (use with care).

## Whitelist / Blacklist
- `whitelist` is a list of command prefixes auto-approved in balanced mode.
- `blacklist_patterns` is always enforced for shell commands.

## Context redaction
- Previews are redacted by `context.redact_keys` (YAML/JSON keys).
- Regex patterns in `context.redact_patterns` replace matched text.
- Sensitive files like `config.yaml` or `.env` are excluded by default.

## Recommendations
- Use environment variables for API keys.
- Avoid storing secrets in the workspace.
- Review tool requests carefully in balanced/paranoid modes.
- Keep `allow_shell=false` unless needed.
