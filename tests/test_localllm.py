"""
Tests for Local LLM backend (LM Studio, Ollama, etc.)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm_providers.localllm import (
    LocalLLMBackend,
    AgentEvent,
    DEFAULT_ENDPOINTS,
    SYSTEM_PROMPT,
    create_backend,
)


class TestLocalLLMBackend:
    """Tests for LocalLLMBackend class."""

    def test_init_with_url(self):
        """Test backend initialization with custom URL."""
        backend = LocalLLMBackend(base_url="http://192.168.1.1:1234/v1")
        assert backend.base_url == "http://192.168.1.1:1234/v1"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from URL."""
        backend = LocalLLMBackend(base_url="http://localhost:1234/v1/")
        assert backend.base_url == "http://localhost:1234/v1"

    def test_init_with_model(self):
        """Test backend initialization with explicit model."""
        backend = LocalLLMBackend(model="test-model")
        assert backend.model == "test-model"

    def test_init_timeout(self):
        """Test backend initialization with custom timeout."""
        backend = LocalLLMBackend(timeout=60)
        assert backend.timeout == 60

    def test_default_endpoints_exist(self):
        """Test that default endpoints are defined."""
        assert "lmstudio" in DEFAULT_ENDPOINTS
        assert "ollama" in DEFAULT_ENDPOINTS
        assert "localai" in DEFAULT_ENDPOINTS

    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        assert len(SYSTEM_PROMPT) > 100
        assert "Agent Zero" in SYSTEM_PROMPT

    def test_parse_tool_call_valid(self):
        """Test parsing valid tool call from response."""
        backend = LocalLLMBackend()
        text = 'I will list the files.\n<tool name="shell" command="ls -la" reason="list files"/>'
        result = backend._parse_tool_call(text)

        assert result is not None
        assert result["name"] == "shell"
        assert result["command"] == "ls -la"
        assert result["reason"] == "list files"

    def test_parse_tool_call_no_match(self):
        """Test parsing text without tool call."""
        backend = LocalLLMBackend()
        result = backend._parse_tool_call("Just regular text without tools")
        assert result is None

    def test_parse_tool_call_read_file(self):
        """Test parsing read_file tool call."""
        backend = LocalLLMBackend()
        text = '<tool name="read_file" command="main.py" reason="read source code"/>'
        result = backend._parse_tool_call(text)

        assert result["name"] == "read_file"
        assert result["command"] == "main.py"

    def test_clean_response_removes_tool(self):
        """Test that tool tags are removed from response."""
        backend = LocalLLMBackend()
        text = 'Let me list files.\n<tool name="shell" command="ls" reason="list"/>'
        result = backend._clean_response(text)

        assert "<tool" not in result
        assert "Let me list files" in result

    def test_clean_response_handles_no_tool(self):
        """Test clean_response with text without tool tags."""
        backend = LocalLLMBackend()
        text = "Just regular text"
        result = backend._clean_response(text)
        assert result == "Just regular text"

    def test_get_stats(self):
        """Test get_stats returns correct structure."""
        backend = LocalLLMBackend(base_url="http://test:1234/v1", model="test-model")
        stats = backend.get_stats()

        assert stats["backend"] == "LocalLLM"
        assert stats["url"] == "http://test:1234/v1"
        assert stats["model"] == "test-model"
        assert stats["history_length"] == 0

    def test_conversation_history_starts_empty(self):
        """Test that conversation history is initially empty."""
        backend = LocalLLMBackend()
        assert len(backend.conversation_history) == 0


class TestAgentEvent:
    """Tests for AgentEvent dataclass."""

    def test_create_event(self):
        """Test creating a basic event."""
        event = AgentEvent(type="thought", content="thinking...")
        assert event.type == "thought"
        assert event.content == "thinking..."
        assert event.tool_call is None

    def test_create_event_with_tool_call(self):
        """Test creating event with tool call."""
        tool = {"name": "shell", "command": "ls"}
        event = AgentEvent(type="tool_request", content="ls", tool_call=tool)
        assert event.tool_call == tool


class TestLocalLLMIntegration:
    """Integration tests (require LOCAL_LLM_URL)."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running LM Studio")
    async def test_send_prompt_real(self):
        """Test real API call to local LLM."""
        import os
        url = os.getenv("LOCAL_LLM_URL", "http://localhost:1234/v1")
        backend = LocalLLMBackend(base_url=url)

        events = []
        async for event in backend.send_prompt("Say hello"):
            events.append(event)

        await backend.close()

        assert len(events) > 0
        assert any(e.type == "final_response" for e in events)


class TestCreateBackend:
    """Tests for create_backend factory function."""

    @patch.dict("os.environ", {"LOCAL_LLM_URL": "http://test:1234/v1"}, clear=False)
    def test_create_backend_uses_env(self):
        """Test that create_backend reads from environment."""
        backend = create_backend()
        assert backend.base_url == "http://test:1234/v1"

    def test_create_backend_with_explicit_url(self):
        """Test create_backend with explicit URL parameter."""
        backend = create_backend(base_url="http://explicit:5678/v1")
        assert backend.base_url == "http://explicit:5678/v1"
