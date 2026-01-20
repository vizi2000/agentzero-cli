"""
Local LLM Backend for AgentZeroCLI

Supports OpenAI-compatible APIs:
- LM Studio (default port 1234)
- Ollama (default port 11434)
- LocalAI
- Text Generation WebUI (oobabooga)
- Any OpenAI-compatible server

Uses standard /v1/chat/completions endpoint.
"""

import json
import os
import httpx
from dataclasses import dataclass
from typing import AsyncGenerator, Optional


@dataclass 
class AgentEvent:
    """Event yielded during agent interaction."""
    type: str
    content: str
    tool_call: Optional[dict] = None


# Default endpoints for common local LLM servers
DEFAULT_ENDPOINTS = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1", 
    "localai": "http://localhost:8080/v1",
}

SYSTEM_PROMPT = """You are Agent Zero, an AI coding assistant running in a terminal.
You help users with coding tasks by analyzing requests and executing tools when needed.

When you need to execute a command, respond with a tool call in this format:
<tool name="shell" command="the command" reason="why you need this"/>

Available tools:
- shell: Execute shell commands
- read_file: Read file contents  
- write_file: Write to a file
- list_files: List directory contents

Always explain your reasoning. Be concise but thorough."""


class LocalLLMBackend:
    """
    Backend for local LLM servers (LM Studio, Ollama, etc.)
    
    Env vars:
    - LOCAL_LLM_URL: Base URL (e.g., http://localhost:1234/v1)
    - LOCAL_LLM_MODEL: Model name (optional, uses first available)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120
    ):
        self.base_url = base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:1234/v1")
        self.base_url = self.base_url.rstrip("/")
        
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.conversation_history: list[dict] = []
        
        # Auto-detect model if not specified
        if not self.model:
            self.model = self._detect_model()
    
    def _detect_model(self) -> str:
        """Detect available model from server."""
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.base_url}/models", timeout=5) as resp:
                data = json.loads(resp.read().decode())
                models = data.get("data", [])
                if models:
                    # Prefer chat models, avoid embedding models
                    for m in models:
                        model_id = m.get("id", "")
                        if "embed" not in model_id.lower():
                            return model_id
                    return models[0].get("id", "default")
        except Exception:
            pass
        return "default"
    
    async def send_prompt(self, user_text: str) -> AsyncGenerator[AgentEvent, None]:
        """Send prompt to local LLM and stream response."""
        yield AgentEvent(type="status", content=f"Using local model: {self.model}")
        
        self.conversation_history.append({
            "role": "user",
            "content": user_text
        })
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history
        ]
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    yield AgentEvent(
                        type="error",
                        content=f"Local LLM error {response.status_code}: {error.decode()[:200]}"
                    )
                    return
                
                full_response = ""
                buffer = ""
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
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
                            
                            # Yield in chunks
                            if len(buffer) > 20 or "\n" in buffer:
                                yield AgentEvent(type="thought", content=buffer)
                                buffer = ""
                                
                    except json.JSONDecodeError:
                        continue
                
                # Remaining buffer
                if buffer:
                    yield AgentEvent(type="thought", content=buffer)
                
                # Check for tool calls
                tool_call = self._parse_tool_call(full_response)
                if tool_call:
                    yield AgentEvent(
                        type="tool_request",
                        content=tool_call["command"],
                        tool_call=tool_call
                    )
                
                # Save to history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": full_response
                })
                
                yield AgentEvent(
                    type="final_response",
                    content=self._clean_response(full_response)
                )
                
        except httpx.ConnectError:
            yield AgentEvent(
                type="error",
                content=f"Cannot connect to local LLM at {self.base_url}. Is LM Studio/Ollama running?"
            )
        except httpx.TimeoutException:
            yield AgentEvent(type="error", content="Local LLM request timed out")
        except Exception as e:
            yield AgentEvent(type="error", content=f"Local LLM error: {str(e)}")
    
    def _parse_tool_call(self, text: str) -> Optional[dict]:
        """Parse tool call from response."""
        import re
        pattern = r'<tool\s+name="([^"]+)"\s+command="([^"]+)"\s+reason="([^"]+)"'
        match = re.search(pattern, text)
        
        if match:
            return {
                "name": match.group(1),
                "command": match.group(2),
                "reason": match.group(3),
            }
        return None
    
    def _clean_response(self, text: str) -> str:
        """Remove tool calls from response."""
        import re
        return re.sub(r'<tool[^>]+/?>', '', text).strip()
    
    async def explain_risk(self, command: str) -> str:
        """Ask local LLM to explain command risk."""
        prompt = f"""Analyze the security risk of this command in max 50 words:
{command}

Format: RISK_LEVEL (LOW/MEDIUM/HIGH): brief explanation"""

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.3,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            return f"Could not analyze: HTTP {response.status_code}"
            
        except Exception as e:
            return f"Could not analyze: {str(e)}"
    
    async def execute_tool(self, tool_name: str, command: str, cwd: str | None = None) -> AsyncGenerator[AgentEvent, None]:
        """Execute tool."""
        from tools.executor import execute_tool as real_execute
        
        async for event in real_execute(tool_name, command, cwd):
            yield AgentEvent(
                type=event.get("type", "status"),
                content=event.get("content", "")
            )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    def get_stats(self) -> dict:
        """Get backend stats."""
        return {
            "backend": "LocalLLM",
            "url": self.base_url,
            "model": self.model,
            "history_length": len(self.conversation_history),
        }


def create_backend(
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> LocalLLMBackend:
    """Create local LLM backend."""
    from dotenv import load_dotenv
    load_dotenv()
    
    return LocalLLMBackend(base_url=base_url, model=model)
