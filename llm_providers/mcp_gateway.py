"""MCP Gateway LLM provider for fallback."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .base import LLMProvider


class MCPGatewayClient(LLMProvider):
    """MCP Gateway client (borg.tools) for LLM inference."""

    BASE_URL = "https://mcp.borg.tools/v1/inference"

    def __init__(self, config: dict[str, Any]):
        """Initialize from observer config section."""
        self.api_key = os.environ.get("MCP_GATEWAY_API_KEY") or config.get("mcp_api_key", "")
        self.timeout = config.get("timeout", 30)

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def complete(self, prompt: str, system: str = "") -> str:
        """Send completion request to MCP Gateway."""
        if not self.api_key:
            return ""

        payload = {"prompt": prompt}
        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.BASE_URL, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", data.get("text", ""))
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError):
            return ""
