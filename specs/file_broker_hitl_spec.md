# File Broker MVP - Human-in-the-Loop (HITL) Specification

## Overview

This specification describes the implementation of a file broker system for Agent Zero CLI that transforms write operations from immediate execution to a propose-then-apply pattern with human approval.

## MVP Behavior Summary

| Operation | Current Behavior | New Behavior |
|-----------|-----------------|--------------|
| `read_file` | Reads file, returns content | Reads file with byte cap, returns content + `base_hash` |
| `write_file` | Writes file immediately | **Proposes only**, stores HITL record, returns `hitl_required` |
| `apply_patch` | Applies patch immediately | **Proposes only**, stores HITL record, returns `hitl_required` |
| `apply_proposal` (NEW) | N/A | Validates HITL record, executes write, deletes record |

## Key MVP Rule

**`write_file` NEVER writes. It only proposes and returns `hitl_required`. Only `apply_proposal` performs the actual write.**

---

## Detailed Specifications

### 1. `read_file` Operation

**Behavior:**
- Reads file with line range support (`start_line`, `end_line`)
- Enforces byte cap (`max_bytes`, default 32KB, hard cap 128KB)
- Blocks path traversal and denylisted paths
- Returns `base_hash` (SHA-256) of full file content

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | required | File path relative to workspace |
| `start_line` | int | 1 | First line to return |
| `end_line` | int | start_line+199 | Last line to return |
| `max_bytes` | int | 32000 | Max bytes to return |

**Response Schema:**
```json
{
  "schema_version": "1.0",
  "status": "allowed",
  "op": {"method": "fs.read", "path": "<path>"},
  "data": {
    "content": "<file content>",
    "returned_range": {"start_line": 1, "end_line": 50},
    "base_hash": "sha256:<64 hex chars>",
    "truncated": false,
    "max_bytes": 32000
  },
  "audit": {"prev_hash": "sha256:...", "event_hash": "sha256:..."}
}
```

---

### 2. `write_file` Operation (Propose Only)

**Behavior:**
- Computes unified diff between current content and new content
- For create operations: diff from `/dev/null` to new path
- Stores short-lived HITL record with TTL (default 120 seconds)
- Returns `status=hitl_required` with diff preview
- **Does NOT write the file**

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | required | File path relative to workspace |
| `content` | string | required | New file content |

**HITL Record Structure:**
```python
{
    "hitl_id": "hitl-<uuid>",
    "path": "<relative path>",
    "full_path": "<absolute path>",
    "created": True/False,  # True if new file
    "base_hash": "sha256:<hash of original content>",
    "diff": "<unified diff text>",
    "new_content": "<proposed content>",
    "patch_hash": "sha256:<hash of diff>",
    "expires_at": <timestamp>,
    "tool_call_id": "<original tool call id>",
    "context_id": "<agent context id>"
}
```

**Response Schema:**
```json
{
  "schema_version": "1.0",
  "status": "hitl_required",
  "op": {"method": "fs.propose_patch", "path": "<path>"},
  "hitl": {
    "hitl_id": "hitl-<uuid>",
    "ttl_seconds": 120,
    "summary": "CREATE FILE <path>" or "MODIFY <path>",
    "diff_preview": "<unified diff, truncated if >8000 chars>"
  },
  "data": {
    "path": "<path>",
    "created": true/false,
    "base_hash": "sha256:...",
    "patch_hash": "sha256:...",
    "patch_format": "unified_diff"
  },
  "audit": {"prev_hash": "sha256:...", "event_hash": "sha256:..."}
}
```

---

### 3. `apply_proposal` Operation (NEW - CLI Only)

**Behavior:**
- Validates `hitl_id` exists and TTL not expired
- Re-hashes current file to ensure `base_hash` matches (TOCTOU protection)
- Writes file (create or modify)
- Deletes HITL record (one-time use)
- Returns result as `tool_name: "write_file"` for agent correlation

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | required | File path (must match HITL record) |
| `hitl_id` | string | required | HITL record identifier |

**Validation Steps:**
1. Check HITL record exists
2. Check path matches record
3. Check TTL not expired
4. Check path not in denylist
5. Re-resolve safe path and compare
6. Re-hash current file content
7. Compare hash with stored `base_hash`
8. If mismatch: reject (file changed since proposal)

**Response Schema:**
```json
{
  "schema_version": "1.0",
  "status": "allowed",
  "op": {"method": "fs.apply_patch", "path": "<path>"},
  "data": {
    "path": "<path>",
    "created": true/false,
    "before_hash": "sha256:...",
    "after_hash": "sha256:...",
    "hitl_id": "<hitl_id>"
  },
  "audit": {"prev_hash": "sha256:...", "event_hash": "sha256:..."}
}
```

---

## Security Features

### Path Sandbox
- All paths must be relative to `workspace_root`
- Absolute paths blocked
- Path traversal (`..`) blocked
- Symlink escape blocked via `realpath` check

### Deny Path Globs
Default denylisted patterns:
```python
[
    "**/.env",
    "**/*.pem",
    "**/*id_rsa*",
    "**/secrets/**",
]
```

### Create Allowlist
New files can only be created in whitelisted directories:
```python
["src/", "lib/", "tests/", "docs/", "scripts/"]
```
Root-level files (no subdirectory) are always allowed.

### Size Limits
| Limit | Default | Hard Cap |
|-------|---------|----------|
| `max_read_bytes_default` | 32KB | 128KB |
| `max_write_bytes_hard` | 512KB | N/A |

### TOCTOU (Time-of-Check-Time-of-Use) Protection
- `base_hash` stored at proposal time
- Current file re-hashed at apply time
- Mismatch = rejection (requires re-proposal)

---

## Audit Trail

### Hash Chain
- Each event linked to previous via `prev_hash`
- Tamper-evident (not tamper-proof in MVP)
- Chain restarts on backend restart (Phase 2: persist state)

### Audit Log Location
```
{workspace_root}/.agentzero_audit.jsonl
```

### Event Types Logged
| Event | Description |
|-------|-------------|
| `read_file` | File read with path, range, base_hash |
| `write_file_propose` | Proposal created with path, base_hash, patch_hash |
| `write_file_apply` | Proposal applied with before_hash, after_hash |

### Audit Record Schema
```json
{
  "ts": "2025-01-13T12:00:00Z",
  "op": "write_file_propose",
  "path": "src/main.py",
  "created": false,
  "base_hash": "sha256:...",
  "patch_hash": "sha256:...",
  "tool_call_id": "tc-123",
  "context_id": "ctx-456",
  "status": "hitl_required",
  "prev_hash": "sha256:...",
  "event_hash": "sha256:..."
}
```

---

## CLI Integration

### Workflow
1. Agent sends `write_file` tool request
2. Backend generates proposal, stores HITL record
3. Backend returns `tool_result` with `status=hitl_required`
4. CLI detects `hitl_required` status
5. CLI shows diff preview to user
6. User approves or rejects
7. If approved: CLI sends `apply_proposal` tool request
8. Backend validates and executes proposal
9. Backend returns `tool_result` as `write_file` (for agent correlation)

### CLI Changes Required
When `tool_result.details.status == "hitl_required"`:
1. Show diff preview to user
2. If approved, send new tool request:
```json
{
  "type": "tool_request",
  "tool_name": "apply_proposal",
  "path": "<same path>",
  "hitl_id": "<from tool_result.details.hitl.hitl_id>"
}
```

---

## Configuration Options

New config.yaml section:
```yaml
file_broker:
  enabled: true
  hitl_ttl_seconds: 120
  max_read_bytes_default: 32000
  max_read_bytes_hard: 131072
  max_write_bytes_hard: 524288
  audit_log_enabled: true
  allowlisted_create_dirs:
    - "src/"
    - "lib/"
    - "tests/"
    - "docs/"
    - "scripts/"
  deny_path_globs:
    - "**/.env"
    - "**/*.pem"
    - "**/*id_rsa*"
    - "**/secrets/**"
```

---

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `backend.py` | Add helpers, modify handlers, add apply_proposal | HIGH |
| `cli/app.py` | Handle hitl_required status, send apply_proposal | HIGH |
| `cli/approval.py` | Extend preview for proposals | MEDIUM |
| `config.yaml` | Add file_broker section | LOW |
| `config.example.yaml` | Add file_broker section | LOW |

---

## Implementation Tasks

### Group A: Backend Core (can run in parallel with Group B)
1. Add imports (hashlib, uuid, difflib, fnmatch, time)
2. Add `_mvp_init_filebroker()` lazy initialization
3. Add helper methods:
   - `_get_param()` - parameter extraction
   - `_sha256_text()` - text hashing
   - `_sha256_file_stream()` - file hashing
   - `_new_hitl_id()` - UUID generation
   - `_hitl_cleanup()` - expired record cleanup
   - `_is_denied_path()` - denylist check
   - `_is_create_allowed()` - allowlist check
   - `_generate_unified_diff()` - diff generation
   - `_audit_append()` - audit logging
   - `_deny_result()` - denied response builder
   - `_error_result()` - error response builder

### Group B: Handler Modifications (can run in parallel with Group A)
1. Modify `_handle_read_file()` - add base_hash, byte cap
2. Modify `_handle_write_file()` - propose only, store HITL

### Group C: New Functionality (depends on A + B)
1. Add `_handle_apply_proposal()` - execute proposals
2. Update `execute_tool()` dispatcher

### Group D: CLI Integration (depends on C)
1. Modify `cli/app.py` - handle hitl_required
2. Update `cli/approval.py` - show proposal info

### Group E: Configuration (can run anytime)
1. Update `config.yaml`
2. Update `config.example.yaml`

---

## Testing Plan

### Unit Tests
- [ ] Test `_is_denied_path()` with various patterns
- [ ] Test `_is_create_allowed()` with various paths
- [ ] Test `_sha256_text()` consistency
- [ ] Test `_generate_unified_diff()` output format
- [ ] Test HITL record expiration

### Integration Tests
- [ ] Test write_file returns hitl_required
- [ ] Test apply_proposal with valid hitl_id
- [ ] Test apply_proposal with expired hitl_id
- [ ] Test apply_proposal with modified file (TOCTOU)
- [ ] Test apply_proposal with path mismatch

### End-to-End Tests
- [ ] Full workflow: write_file → approve → apply_proposal
- [ ] Create new file workflow
- [ ] Modify existing file workflow
- [ ] Reject proposal workflow

---

## Future Extensions (Phase 2)

1. **Persistent HITL Store** - Survive backend restarts
2. **SIEM Integration** - External audit log shipping
3. **Granular Permissions** - Per-path approval rules
4. **Batch Proposals** - Group multiple changes
5. **Rollback Support** - Undo applied changes
6. **Diff Engine** - Apply actual patches instead of full content

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-13 | AI | Initial MVP specification |
