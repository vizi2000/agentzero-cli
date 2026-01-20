"""
OpenRouter Backend for AgentZeroCLI
Real LLM integration with load balancing
"""
import os
import json
import random
import httpx
from typing import AsyncGenerator, Optional, List
from dataclasses import dataclass

# Default models for load balancing
DEFAULT_MODELS = [
    "openrouter/polaris-alpha",
    "mistralai/devstral-2512:free",
    "xiaomi/mimo-v2-flash:free"
]


@dataclass
class ToolCall:
    """Represents a tool call request from the LLM"""
    name: str
    command: str
    reason: str
    risk_level: str = "medium"


@dataclass
class AgentEvent:
    """Event yielded during agent interaction"""
    type: str  # status, thought, tool_request, tool_output, final_response, error
    content: str
    tool_call: Optional[ToolCall] = None


class OpenRouterBackend:
    """
    Real OpenRouter backend for AgentZeroCLI.
    Supports streaming responses, tool calling, and load balancing.
    """
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    SYSTEM_PROMPT = """You are Agent Zero, an AI coding assistant running in a terminal.
You help users with coding tasks by:
1. Analyzing their requests
2. Planning the approach (think step by step)
3. Executing tools when needed (file operations, shell commands, git)
4. Explaining what you're doing

IMPORTANT: When you need to execute a command, respond with a tool call in this format:
<tool name="shell" command="the command" reason="why you need this"/>

Available tools:
- shell: Execute shell commands
- read_file: Read file contents
- write_file: Write to a file
- edit_file: Edit a file

Always explain your reasoning before executing commands.
Be concise but thorough. Prioritize user safety."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        models: Optional[List[str]] = None,
        timeout: int = 60
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        # Load models from env or use defaults
        models_env = os.getenv("OPENROUTER_MODELS", "")
        if models:
            self.models = models
        elif models_env:
            self.models = [m.strip() for m in models_env.split(",")]
        else:
            self.models = DEFAULT_MODELS
        
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.conversation_history: list[dict] = []
        self.current_model_index = 0
        self.request_count = 0
    
    def _get_next_model(self) -> str:
        """Round-robin load balancing between models"""
        model = self.models[self.current_model_index]
        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        self.request_count += 1
        return model
    
    def _get_random_model(self) -> str:
        """Random model selection"""
        return random.choice(self.models)
    
    async def send_prompt(self, user_text: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Send a prompt to the LLM and stream the response.
        Yields AgentEvent objects for different response types.
        """
        model = self._get_next_model()
        yield AgentEvent(type="status", content=f"Using model: {model}")
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_text
        })
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *self.conversation_history
        ]
        
        try:
            async with self.client.stream(
                "POST",
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://agentzerocli.dev",
                    "X-Title": "AgentZeroCLI"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 4096
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield AgentEvent(
                        type="error",
                        content=f"API Error {response.status_code}: {error_text.decode()}"
                    )
                    return
                
                full_response = ""
                buffer = ""
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                full_response += content
                                buffer += content
                                
                                # Yield chunks for streaming display
                                if len(buffer) > 10 or "\n" in buffer:
                                    yield AgentEvent(
                                        type="thought",
                                        content=buffer
                                    )
                                    buffer = ""
                                
                        except json.JSONDecodeError:
                            continue
                
                # Yield remaining buffer
                if buffer:
                    yield AgentEvent(type="thought", content=buffer)
                
                # Check for tool calls in full response
                tool_call = self._parse_tool_call(full_response)
                if tool_call:
                    yield AgentEvent(
                        type="tool_request",
                        content=tool_call.command,
                        tool_call=tool_call
                    )
                
                # Save assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })
                
                # Final response
                yield AgentEvent(
                    type="final_response",
                    content=self._clean_response(full_response)
                )
                
        except httpx.TimeoutException:
            yield AgentEvent(type="error", content="Request timed out - try again")
        except httpx.ConnectError:
            yield AgentEvent(type="error", content="Connection failed - check internet")
        except Exception as e:
            yield AgentEvent(type="error", content=f"Error: {str(e)}")
    
    async def explain_risk(self, command: str) -> str:
        """Ask the LLM to explain the risk of a command."""
        model = self._get_random_model()
        
        prompt = f"""Analyze the security risk of this command:
```
{command}
```

Explain briefly:
1. What this command does
2. Risk level (LOW/MEDIUM/HIGH/CRITICAL)
3. Recommendation

Be concise (max 100 words)."""

        try:
            response = await self.client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://agentzerocli.dev"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Could not analyze risk: API error {response.status_code}"
                
        except Exception as e:
            return f"Could not analyze risk: {str(e)}"
    
    async def execute_tool(self, tool_name: str, command: str, cwd: str | None = None) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute a tool and stream results.
        
        Args:
            tool_name: Type of tool (shell, read_file, etc.)
            command: Command or arguments
            cwd: Working directory
        """
        # Import here to avoid circular imports
        from .tools.executor import execute_tool as real_execute
        
        async for event in real_execute(tool_name, command, cwd):
            yield AgentEvent(
                type=event.get("type", "status"),
                content=event.get("content", "")
            )
    
    def _parse_tool_call(self, text: str) -> Optional[ToolCall]:
        """Parse tool call from LLM response"""
        import re
        
        # Match <tool name="..." command="..." reason="..."/>
        pattern = r'<tool\s+name="([^"]+)"\s+command="([^"]+)"\s+reason="([^"]+)"'
        match = re.search(pattern, text)
        
        if match:
            return ToolCall(
                name=match.group(1),
                command=match.group(2),
                reason=match.group(3)
            )
        return None
    
    def _clean_response(self, text: str) -> str:
        """Remove tool calls from final response"""
        import re
        return re.sub(r'<tool[^>]+/?>', '', text).strip()
    
    def get_stats(self) -> dict:
        """Get backend statistics"""
        return {
            "models": self.models,
            "current_index": self.current_model_index,
            "total_requests": self.request_count,
            "history_length": len(self.conversation_history)
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


def create_backend(
    api_key: Optional[str] = None,
    models: Optional[List[str]] = None
) -> OpenRouterBackend:
    """Create an OpenRouter backend with optional config override"""
    from dotenv import load_dotenv
    load_dotenv()
    
    return OpenRouterBackend(
        api_key=api_key,
        models=models
    )
