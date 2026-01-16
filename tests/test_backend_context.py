import pytest

from backend import RemoteAgentBackend


def _build_backend(tmp_path):
    config = {
        "connection": {
            "api_url": "http://example.local/api_message",
            "workspace_root": str(tmp_path),
            "stream": False,
        },
        "context": {
            "include_previews": True,
            "preview_files": ["secret.txt", "config.example.yaml"],
            "redact_keys": ["api_key", "token"],
            "redact_patterns": ["(?i)bearer\\s+[A-Za-z0-9._-]+"],
        },
    }
    return RemoteAgentBackend(config)


def test_preview_redacts_sensitive_keys(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("api_key: super-secret\nother: value")
    backend = _build_backend(tmp_path)

    preview = backend._read_preview("secret.txt")
    assert preview is not None
    assert "super-secret" not in preview
    assert "***REDACTED***" in preview


def test_context_id_extracted_from_response(tmp_path):
    backend = _build_backend(tmp_path)
    payload = {"context_id": "ctx-123", "response": {"type": "status", "content": "ok"}}
    events = list(backend._extract_events(payload))
    assert backend.context_id == "ctx-123"
    assert any(event.get("type") == "status" for event in events)


def test_sensitive_files_are_skipped(tmp_path):
    config_file = tmp_path / "config.example.yaml"
    config_file.write_text("api_key: keep")
    backend = _build_backend(tmp_path)
    previews = backend._select_preview_files(["config.example.yaml", "README.md"])
    assert "config.example.yaml" in previews


def test_resolve_safe_path_rejects_symlink(tmp_path):
    ws = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    ws.mkdir()
    outside.write_text("secret")
    link = ws / "out"
    link.symlink_to(outside)

    backend = _build_backend(ws)

    with pytest.raises(ValueError):
        backend._resolve_safe_path("out")


def test_sensitive_file_wildcards(tmp_path):
    backend = _build_backend(tmp_path)
    backend.context_preview_files = ["server.key", "README.md"]
    records = ["server.key", "README.md"]
    previews = backend._select_preview_files(records)
    assert "server.key" not in previews
    assert "README.md" in previews


def test_observer_summary_included_on_change(tmp_path):
    config = {
        "connection": {
            "api_url": "http://example.local/api_message",
            "workspace_root": str(tmp_path),
            "stream": False,
        },
        "context": {"enabled": False},
        "observer": {"enabled": True, "mode": "automatic"},
    }
    backend = RemoteAgentBackend(config)

    message, context_included, observer_included = backend._prepare_message("hello")
    assert observer_included is True
    assert context_included is False
    assert "[AZ_OBSERVER v1]" in message

    message, context_included, observer_included = backend._prepare_message("hello")
    assert observer_included is False
    assert context_included is False
    assert message == "hello"
