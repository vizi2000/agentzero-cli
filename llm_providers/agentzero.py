"""
Agent Zero API Backend for AgentZeroCLI

Connects to self-hosted Agent Zero instance as LLM backend.
Alternative to OpenRouter when you have your own Agent Zero server.
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
import asyncio
import httpx


@dataclass
class AgentEvent:
    """Event yielded during agent interaction."""
    type: str  # status, thought, tool_request, tool_output, final_response, error
    content: str
    tool_call: Optional[dict] = None


class AgentZeroBackend:
    """
    Backend connecting to Agent Zero API.
    
    Requires:
    - AGENTZERO_API_URL: URL to Agent Zero API (e.g., http://localhost:50001/api_message)
    - AGENTZERO_API_KEY: API key for authentication (optional)
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 120
    ):
        self.api_url = api_url or os.getenv("AGENTZERO_API_URL")
        if not self.api_url:
            raise ValueError("AGENTZERO_API_URL not set")
        
        self.api_key = api_key or os.getenv("AGENTZERO_API_KEY", "")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.conversation_id: Optional[str] = None
    
    async def send_prompt(self, user_text: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Send a prompt to Agent Zero and stream the response.
        """
        yield AgentEvent(type="status", content="Connecting to Agent Zero...")
        
        payload = {
            "message": user_text,
            "stream": True,
        }
        
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        
        try:
            async with self.client.stream(
                "POST",
                self.api_url,
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield AgentEvent(
                        type="error",
                        content=f"Agent Zero API Error {response.status_code}: {error_text.decode()[:200]}"
                    )
                    return
                
                full_response = ""
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # Handle SSE format
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    if line == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(line)
                        
                        # Extract conversation ID for continuation
                        if "conversation_id" in data:
                            self.conversation_id = data["conversation_id"]
                        
                        # Handle different event types from Agent Zero
                        event_type = data.get("type", "")
                        content = data.get("content", data.get("message", data.get("text", "")))
                        
                        if event_type == "thinking" or event_type == "thought":
                            yield AgentEvent(type="thought", content=content)
                            
                        elif event_type == "tool_call" or event_type == "tool_request":
                            tool_name = data.get("tool_name", data.get("name", "shell"))
                            command = data.get("command", data.get("args", ""))
                            reason = data.get("reason", "Agent requested tool execution")
                            
                            yield AgentEvent(
                                type="tool_request",
                                content=command,
                                tool_call={
                                    "name": tool_name,
                                    "command": command,
                                    "reason": reason,
                                }
                            )
                            
                        elif event_type == "response" or event_type == "message":
                            full_response += content
                            yield AgentEvent(type="thought", content=content)
                            
                        elif event_type == "error":
                            yield AgentEvent(type="error", content=content)
                            
                        elif event_type == "status":
                            yield AgentEvent(type="status", content=content)
                            
                        else:
                            # Default: treat as response chunk
                            if content:
                                full_response += content
                                yield AgentEvent(type="thought", content=content)
                                
                    except json.JSONDecodeError:
                        # Plain text response
                        if line.strip():
                            full_response += line
                            yield AgentEvent(type="thought", content=line)
                
                # Final response
                if full_response:
                    yield AgentEvent(type="final_response", content=full_response.strip())
                    
        except httpx.TimeoutException:
            yield AgentEvent(type="error", content="Agent Zero request timed out")
        except httpx.ConnectError:
            yield AgentEvent(type="error", content="Cannot connect to Agent Zero - is it running?")
        except Exception as e:
            yield AgentEvent(type="error", content=f"Agent Zero error: {str(e)}")
    
    async def explain_risk(self, command: str) -> str:
        """Ask Agent Zero to explain command risk."""
        prompt = f"Briefly analyze the security risk of this command (max 100 words):\n{command}"
        
        try:
            response = await self.client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    **({"X-API-KEY": self.api_key} if self.api_key else {})
                },
                json={"message": prompt, "stream": False}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", data.get("content", data.get("response", str(data))))
            else:
                return f"Could not analyze: API error {response.status_code}"
                
        except Exception as e:
            return f"Could not analyze: {str(e)}"
    
    async def execute_tool(self, tool_name: str, command: str, cwd: str | None = None) -> AsyncGenerator[AgentEvent, None]:
        """Execute a tool and stream results."""
        from tools.executor import execute_tool as real_execute
        
        async for event in real_execute(tool_name, command, cwd):
            yield AgentEvent(
                type=event.get("type", "status"),
                content=event.get("content", "")
            )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def get_stats(self) -> dict:
        """Get backend statistics."""
        return {
            "backend": "AgentZero",
            "api_url": self.api_url,
            "conversation_id": self.conversation_id,
            "has_api_key": bool(self.api_key),
        }


def create_backend(
    api_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> AgentZeroBackend:
    """Create an Agent Zero backend."""
    from dotenv import load_dotenv
    load_dotenv()
    
    return AgentZeroBackend(api_url=api_url, api_key=api_key)
