"""
Backend factory for AgentZeroCLI

Priority order (by capability):
1. OpenRouter - cloud LLMs, best quality, data leaves network
2. Agent Zero API - self-hosted, good quality, your infrastructure  
3. Local LLM - Ollama/LM Studio, SAFEST (data stays local), good quality
4. Local Deterministic - pattern matching, offline, no LLM

SECURITY NOTE:
All backends go through the same security flow:
  User Input → Backend → tool_request → ToolApprovalScreen → execute

The security interceptor is NEVER bypassed regardless of backend.
See docs/SECURITY.md for details.
"""

import os
from typing import Protocol, AsyncGenerator, Any


class BackendProtocol(Protocol):
    """Protocol for all backends."""
    
    async def send_prompt(self, user_text: str) -> AsyncGenerator[Any, None]: ...
    async def explain_risk(self, command: str) -> str: ...
    async def execute_tool(self, tool_name: str, command: str, cwd: str | None = None) -> AsyncGenerator[Any, None]: ...
    async def close(self) -> None: ...


def get_backend() -> BackendProtocol:
    """
    Factory function to get the best available backend.
    
    Priority (checks in order, uses first available):
    1. Local LLM (SAFEST) - if LOCAL_LLM_URL is set - data stays on your network
    2. Agent Zero API - if AGENTZERO_API_URL is set - self-hosted
    3. OpenRouter - if OPENROUTER_API_KEY is set - cloud LLMs, best quality
    4. Local Deterministic - always available, pattern matching, no LLM
    
    All tool_requests go through ToolApprovalScreen regardless of backend.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    # Priority 1: Local LLM (SAFEST - data never leaves your network)
    local_llm_url = os.getenv("LOCAL_LLM_URL")
    if local_llm_url:
        try:
            from .llm_providers.localllm import LocalLLMBackend
            backend = LocalLLMBackend(base_url=local_llm_url)
            print(f"[OK] Local LLM connected - {backend.model} (SAFEST)")
            return backend
        except ImportError as e:
            print(f"[WARN] LocalLLM import failed: {e}")
        except Exception as e:
            print(f"[WARN] LocalLLM init failed: {e}")
    
    # Priority 2: Agent Zero API (self-hosted)
    agentzero_url = os.getenv("AGENTZERO_API_URL")
    if agentzero_url:
        try:
            from .llm_providers.agentzero import AgentZeroBackend
            backend = AgentZeroBackend(api_url=agentzero_url)
            print(f"[OK] Agent Zero connected ({agentzero_url})")
            return backend
        except ImportError as e:
            print(f"[WARN] AgentZero import failed: {e}")
        except Exception as e:
            print(f"[WARN] AgentZero init failed: {e}")
    
    # Priority 3: OpenRouter (cloud - data leaves network)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from .llm_providers.openrouter import OpenRouterBackend
            backend = OpenRouterBackend(api_key=openrouter_key)
            print(f"[OK] OpenRouter connected ({len(backend.models)} models)")
            return backend
        except ImportError as e:
            print(f"[WARN] OpenRouter import failed: {e}")
        except Exception as e:
            print(f"[WARN] OpenRouter init failed: {e}")
    
    # Priority 4: Local deterministic (no LLM, always works)
    try:
        from .llm_providers.local import LocalBackend
        backend = LocalBackend()
        print("[OK] Local mode (pattern matching, no LLM)")
        print("[INFO] For AI responses, set LOCAL_LLM_URL, AGENTZERO_API_URL, or OPENROUTER_API_KEY")
        return backend
    except ImportError:
        pass
    
    # Fallback: Minimal mock (should never reach here)
    print("[WARN] No backend available, using minimal mock")
    return MinimalMockBackend()


class MinimalMockBackend:
    """Absolute minimal fallback - should never be used in practice."""
    
    async def send_prompt(self, user_text: str):
        yield {
            "type": "final_response", 
            "content": "No backend configured. Set OPENROUTER_API_KEY or AGENTZERO_API_URL in .env"
        }
    
    async def explain_risk(self, command: str) -> str:
        return f"Cannot analyze '{command}' - no backend configured."
    
    async def execute_tool(self, tool_name: str = "shell", command: str = "", cwd: str | None = None):
        from .tools.executor import execute_tool as real_execute
        async for event in real_execute(tool_name, command, cwd):
            yield event
    
    async def close(self):
        pass


# Backwards compatibility
__all__ = ["get_backend", "BackendProtocol"]
