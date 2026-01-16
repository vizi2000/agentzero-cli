# Agent Zero CLI Next Steps Specification

## Summary
This specification captures the next batch of work for Agent Zero CLI that we will deliver prior to a public Beta announcement. The focus is on hardening the security surface around file access/context generation, aligning documentation with what exists in the repo, and giving operators a clear, step-by-step usage + community playbook.

## Goals
1. Ensure context snapshots and tool workflows never leak values outside the workspace or through sensitive file previews.
2. Define how CLI/TUI operators should run the software, approve tool calls, and verify tool outcomes.
3. Provide transparent instructions for contributors (tests, local development) and users (flows/use cases) so this can ship as an open-source Beta release.
4. Document the outreach plan so community members know where to find the release and how to give feedback.

## Scope
- Backend: `RemoteAgentBackend` controls context snapshots (tree + previews), tool execution, and safe-path enforcement.
- UI/CLI: slash commands, tool approvals, and documentation are the primary touchpoints for users.
- Docs: README, `docs/USAGE.md`, `docs/COMMUNITY.md`, and the new operator guide that aggregates usage, security, and testing guidance.

## Security Requirements
| Area | Requirement | Acceptance Criteria |
| --- | --- | --- |
| Safe paths | No tool may read/write outside the configured `workspace_root`, even via symlinks. | `_resolve_safe_path` canonicalizes both the root and requested path before validating, returning a path within the workspace. |
| Previews | Context previews must skip files that match known-sensitive filenames/patterns, including wildcard entries (e.g., `*.pem`). | `_select_preview_files` filters by matching candidate paths against the sensitive pattern list using glob semantics. |
| Redaction | Any preview content that contains configured `context.redact_keys` or `context.redact_patterns` must replace values with `***REDACTED***`. | Current `_redact_preview_content` handles these patterns, and new tests can validate (if added later). |

## Operator Workflow
1. **Setup**: Install dependencies via `pip install -r requirements.txt` (or `pip install -e .` for editable installs), copy `config.example.yaml`, and set `AGENTZERO_API_URL`/`AGENTZERO_API_KEY` via environment.
2. **Running**: Use `python main_new.py` or `./a0` for the Textual TUI; `python cli.py` / `./a0 --cli` for the CLI. In TUI, type prompts, use F1-F3 shortcuts, and `/help` slash command list for extra operations.
3. **Tool approvals**: Security modes (`paranoid`, `balanced`, `god_mode`) control auto-approval. CLI mode uses `ToolApprovalHandler` rules (auto-approve read-only, whitelist shell prefix). The UI always shows approval dialogs.
4. **Context builder**: Enabled by default; modes `on_change`, `always`, `once`, `manual` determine when the `[AZ_CONTEXT]` bundle is prepended. Previews are redacted and limited to configured `max_bytes`/`max_preview_bytes` to avoid leaking secrets.
5. **Uploads & workspace**: `/upload` copies files into `<workspace_root>/uploads`, guaranteeing the agent operates on local copies. Build-in doc screen handles picking files.
6. **Example flows**:
   - *Audit a repo*: enable `context.mode=on_change`, use `/status` to confirm `context_id`, approve read-only tool calls, and rely on the context summary shown in the live feed.
   - *Patch a config*: change to `paranoid`, run `write_file`/`apply_patch`, review preview, and decide via tool approval.

## Use Cases
1. **Security analyst** wants to interact with Agent Zero without exposing secrets: uses `paranoid` mode, context redaction (ensured by spec), and rejects risky shell commands.
2. **Developer needing automation**: switches to `balanced`, runs read-only commands like `list_files`, uses `/upload` to bring in additional specs, approves safe writes, and examines final responses in the live feed.
3. **Contributor testing CLI**: runs `PYTHONPATH=. pytest` (or `pip install -e .` first) to keep imports working, monitors SSE flows in `tests/test_e2e.py`, and uses `/status` to verify streaming.

## Community & Outreach
- Leverage `docs/COMMUNITY.md` templates to announce the Beta on Agent Zero forums (Polish/English). Replace `<LINK>` placeholders with `https://github.com/agentzero/AgentZeroCLI` for the repo and `https://github.com/agentzero/AgentZeroCLI#readme` for docs.
- Mention open issues from `docs/ISSUES.md` when soliciting feedback.

## Acceptance Criteria
- Backend enforces canonical path checks and wildcard-sensitive preview filtering.
- README/dev instructions mention `PYTHONPATH` or editable install to make tests pass.
- New operator guide consolidates usage, security modes, tool approvals, and use cases.
- Community doc templates reference the Beta release and include pointers to repo/docs.
- Tests (`PYTHONPATH=. pytest`) continue to pass.
