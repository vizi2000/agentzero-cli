"""OpenRouter LLM provider using stdlib urllib."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .base import LLMProvider


class OpenRouterClient(LLMProvider):
    """OpenRouter API client for LLM completions."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, config: dict[str, Any]):
        """Initialize from observer config section."""
        self.api_key = os.environ.get("OPENROUTER_API_KEY") or config.get("api_key", "")
        self.model = config.get("model", "openai/gpt-4o-mini")
        self.timeout = config.get("timeout", 30)

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def complete(self, prompt: str, system: str = "") -> str:
        """Send completion request to OpenRouter."""
        if not self.api_key:
            return ""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 500,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/agentzero-cli",
        }

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.BASE_URL, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError):
            return ""
