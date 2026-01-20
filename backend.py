"""
Backend factory for AgentZeroCLI

Priority order:
1. OpenRouter (if OPENROUTER_API_KEY set) - best quality, cloud LLMs
2. Agent Zero API (if AGENTZERO_API_URL set) - self-hosted Agent Zero
3. Local Deterministic (always available) - pattern matching, no LLM

All backends go through the same security flow:
  User Input → Backend → tool_request → ToolApprovalScreen → execute
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
    
    Priority:
    1. OpenRouter (cloud LLMs) - if OPENROUTER_API_KEY is set
    2. Agent Zero API (self-hosted) - if AGENTZERO_API_URL is set
    3. Local Deterministic - always available, pattern matching
    
    All tool_requests go through ToolApprovalScreen regardless of backend.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    # Priority 1: OpenRouter (best quality, multiple models)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from llm_providers.openrouter import OpenRouterBackend
            backend = OpenRouterBackend(api_key=openrouter_key)
            print(f"[OK] OpenRouter connected ({len(backend.models)} models)")
            return backend
        except ImportError as e:
            print(f"[WARN] OpenRouter import failed: {e}")
        except Exception as e:
            print(f"[WARN] OpenRouter init failed: {e}")
    
    # Priority 2: Agent Zero API (self-hosted)
    agentzero_url = os.getenv("AGENTZERO_API_URL")
    if agentzero_url:
        try:
            from llm_providers.agentzero import AgentZeroBackend
            backend = AgentZeroBackend(api_url=agentzero_url)
            print(f"[OK] Agent Zero connected ({agentzero_url})")
            return backend
        except ImportError as e:
            print(f"[WARN] AgentZero import failed: {e}")
        except Exception as e:
            print(f"[WARN] AgentZero init failed: {e}")
    
    # Priority 3: Local deterministic (always works)
    try:
        from llm_providers.local import LocalBackend
        backend = LocalBackend()
        print("[OK] Local mode (pattern matching, no LLM)")
        print("[INFO] For AI responses, set OPENROUTER_API_KEY or AGENTZERO_API_URL")
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
        from tools.executor import execute_tool as real_execute
        async for event in real_execute(tool_name, command, cwd):
            yield event
    
    async def close(self):
        pass


# Backwards compatibility
__all__ = ["get_backend", "BackendProtocol"]
