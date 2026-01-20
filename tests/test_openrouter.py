"""
Tests for OpenRouter Backend
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add parent to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_providers.openrouter import (
    OpenRouterBackend,
    AgentEvent,
    ToolCall,
    DEFAULT_MODELS,
    create_backend
)
from backend import get_backend
from llm_providers.local import LocalBackend


class TestOpenRouterBackend:
    """Tests for OpenRouterBackend class"""
    
    def test_init_with_api_key(self):
        """Test initialization with API key"""
        backend = OpenRouterBackend(api_key="test-key")
        assert backend.api_key == "test-key"
        assert backend.models == DEFAULT_MODELS
        assert backend.current_model_index == 0
    
    def test_init_with_custom_models(self):
        """Test initialization with custom models"""
        custom_models = ["model1", "model2"]
        backend = OpenRouterBackend(api_key="test-key", models=custom_models)
        assert backend.models == custom_models
    
    def test_init_without_api_key_raises(self):
        """Test that missing API key raises ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
                OpenRouterBackend()
    
    def test_round_robin_model_selection(self):
        """Test round-robin load balancing"""
        backend = OpenRouterBackend(
            api_key="test-key",
            models=["model-a", "model-b", "model-c"]
        )
        
        assert backend._get_next_model() == "model-a"
        assert backend._get_next_model() == "model-b"
        assert backend._get_next_model() == "model-c"
        assert backend._get_next_model() == "model-a"  # wraps around
        assert backend.request_count == 4
    
    def test_random_model_selection(self):
        """Test random model selection"""
        backend = OpenRouterBackend(
            api_key="test-key",
            models=["model-a", "model-b", "model-c"]
        )
        
        # Just verify it returns one of the models
        model = backend._get_random_model()
        assert model in backend.models
    
    def test_parse_tool_call_valid(self):
        """Test parsing valid tool call"""
        backend = OpenRouterBackend(api_key="test-key")
        
        text = 'Let me check files. <tool name="shell" command="ls -la" reason="list files"/>'
        tool_call = backend._parse_tool_call(text)
        
        assert tool_call is not None
        assert tool_call.name == "shell"
        assert tool_call.command == "ls -la"
        assert tool_call.reason == "list files"
    
    def test_parse_tool_call_no_match(self):
        """Test parsing text without tool call"""
        backend = OpenRouterBackend(api_key="test-key")
        
        text = "Just a normal response without any tool calls."
        tool_call = backend._parse_tool_call(text)
        
        assert tool_call is None
    
    def test_clean_response(self):
        """Test removing tool calls from response"""
        backend = OpenRouterBackend(api_key="test-key")
        
        text = 'Here is result <tool name="shell" command="ls" reason="test"/> done'
        cleaned = backend._clean_response(text)
        
        assert "<tool" not in cleaned
        assert "Here is result" in cleaned
        assert "done" in cleaned
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        backend = OpenRouterBackend(
            api_key="test-key",
            models=["m1", "m2"]
        )
        
        # Make some requests to update stats
        backend._get_next_model()
        backend._get_next_model()
        
        stats = backend.get_stats()
        
        assert stats["models"] == ["m1", "m2"]
        assert stats["total_requests"] == 2
        assert stats["current_index"] == 0  # wrapped around
        assert stats["history_length"] == 0


class TestAgentEvent:
    """Tests for AgentEvent dataclass"""
    
    def test_create_event(self):
        """Test creating an AgentEvent"""
        event = AgentEvent(type="thought", content="Thinking...")
        assert event.type == "thought"
        assert event.content == "Thinking..."
        assert event.tool_call is None
    
    def test_create_event_with_tool_call(self):
        """Test creating an AgentEvent with tool call"""
        tool = ToolCall(name="shell", command="pwd", reason="get dir")
        event = AgentEvent(type="tool_request", content="pwd", tool_call=tool)
        
        assert event.type == "tool_request"
        assert event.tool_call.name == "shell"
        assert event.tool_call.command == "pwd"


class TestToolCall:
    """Tests for ToolCall dataclass"""
    
    def test_create_tool_call(self):
        """Test creating a ToolCall"""
        tool = ToolCall(
            name="read_file",
            command="cat README.md",
            reason="Read documentation"
        )
        
        assert tool.name == "read_file"
        assert tool.command == "cat README.md"
        assert tool.reason == "Read documentation"
        assert tool.risk_level == "medium"  # default
    
    def test_create_tool_call_with_risk(self):
        """Test creating a ToolCall with custom risk level"""
        tool = ToolCall(
            name="shell",
            command="rm -rf /tmp/test",
            reason="cleanup",
            risk_level="high"
        )
        
        assert tool.risk_level == "high"


class TestBackendFactory:
    """Tests for backend factory function"""
    
    def test_get_backend_returns_openrouter_with_key(self):
        """Test that OpenRouterBackend is returned with API key"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"}):
            backend = get_backend()
            assert isinstance(backend, OpenRouterBackend)


class TestLocalBackend:
    """Tests for LocalBackend (deterministic, no LLM)"""
    
    @pytest.mark.asyncio
    async def test_send_prompt_yields_events(self):
        """Test that send_prompt yields expected event types"""
        backend = LocalBackend()
        events = []
        
        async for event in backend.send_prompt("list files"):
            events.append(event)
        
        # Should have status and tool_request for known patterns
        event_types = [e.type for e in events]
        assert "status" in event_types
        assert "tool_request" in event_types
    
    @pytest.mark.asyncio
    async def test_help_response(self):
        """Test help request returns info response"""
        backend = LocalBackend()
        events = []
        
        async for event in backend.send_prompt("help"):
            events.append(event)
        
        event_types = [e.type for e in events]
        assert "final_response" in event_types
    
    @pytest.mark.asyncio
    async def test_explain_risk(self):
        """Test risk explanation"""
        backend = LocalBackend()
        result = await backend.explain_risk("rm -rf /")
        
        assert "HIGH RISK" in result
    
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution"""
        backend = LocalBackend()
        events = []
        
        async for event in backend.execute_tool("shell", "echo test"):
            events.append(event)
        
        event_types = [e.type for e in events]
        assert "status" in event_types
        assert "tool_output" in event_types


class TestOpenRouterIntegration:
    """Integration tests (require API key, skipped in CI)"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY not set"
    )
    async def test_real_api_call(self):
        """Test real API call (only runs with valid API key)"""
        from dotenv import load_dotenv
        load_dotenv()
        
        backend = OpenRouterBackend()
        events = []
        
        async for event in backend.send_prompt("Say 'test' and nothing else"):
            events.append(event)
        
        await backend.close()
        
        # Should have at least status and final_response
        event_types = [e.type for e in events]
        assert "status" in event_types
        assert "final_response" in event_types or "error" in event_types
