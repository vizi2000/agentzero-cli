"""
Backend factory for AgentZeroCLI
Auto-detects available backends (OpenRouter or Mock)
"""
import os
import asyncio


class MockAgentBackend:
    """
    Mock backend for offline/demo mode.
    Used when OPENROUTER_API_KEY is not set.
    """

    async def send_prompt(self, user_text: str):
        """Simulate sending prompt and receiving stream of thoughts."""
        
        yield {"type": "status", "content": "[MOCK MODE] Simulating response..."}
        await asyncio.sleep(0.3)
        
        yield {"type": "thought", "content": f"Processing: '{user_text}'"}
        await asyncio.sleep(0.5)

        thoughts = [
            "Analyzing project structure...",
            "Found relevant files.",
            "Preparing response..."
        ]

        for thought in thoughts:
            yield {"type": "thought", "content": thought}
            await asyncio.sleep(0.4)

        # Simulate tool request
        yield {
            "type": "tool_request",
            "tool_name": "shell",
            "command": "ls -la",
            "reason": "List files to understand project structure.",
            "risk_level": "low"
        }

    async def explain_risk(self, command: str):
        """Simulate risk explanation."""
        await asyncio.sleep(0.5)
        return (
            f"[MOCK] Command: {command}\n"
            f"Risk Level: LOW\n"
            f"This is a simulated analysis."
        )

    async def execute_tool(self, tool_name: str = "shell", command: str = "", cwd: str | None = None):
        """Execute tool (real execution even in mock mode)."""
        from tools.executor import execute_tool as real_execute
        
        async for event in real_execute(tool_name, command, cwd):
            yield event


def get_backend():
    """
    Factory function to get the appropriate backend.
    Returns OpenRouterBackend if API key is set, otherwise MockAgentBackend.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if api_key:
        try:
            from llm_providers.openrouter import OpenRouterBackend
            backend = OpenRouterBackend(api_key=api_key)
            print(f"[green]✓[/green] OpenRouter connected ({len(backend.models)} models)")
            return backend
        except ImportError as e:
            print(f"[yellow]⚠[/yellow] OpenRouter import failed: {e}")
            print("[yellow]⚠[/yellow] Falling back to mock backend")
            return MockAgentBackend()
        except Exception as e:
            print(f"[yellow]⚠[/yellow] OpenRouter init failed: {e}")
            return MockAgentBackend()
    else:
        print("[yellow]⚠[/yellow] No API key - using mock backend")
        print("[dim]Set OPENROUTER_API_KEY in .env for real AI[/dim]")
        return MockAgentBackend()


# For backwards compatibility
__all__ = ["MockAgentBackend", "get_backend"]
