"""Hybrid observer router: rules first, LLM fallback for edge cases."""

import logging
from typing import Any

from .rules import route_by_rules


class ObserverRouter:
    """Routes tool requests using rules + optional LLM fallback."""

    def __init__(self, config: dict[str, Any]):
        """Initialize from config.yaml."""
        self.logger = logging.getLogger("agentzero.observer")
        observer_cfg = config.get("observer", {})
        security_cfg = config.get("security", {})

        self.enabled = observer_cfg.get("enabled", False)
        self.security_mode = security_cfg.get("mode", "balanced")
        self.whitelist = security_cfg.get("whitelist", [])
        self.blacklist = security_cfg.get("blacklist_patterns", [])

        # LLM fallback provider (lazy loaded)
        self.llm_provider = None
        self._provider_name = observer_cfg.get("provider", "")
        self._observer_cfg = observer_cfg

    def _init_llm_provider(self):
        """Lazy-load LLM provider on first use."""
        if self.llm_provider is not None:
            return

        if self._provider_name == "openrouter":
            from .llm_providers import OpenRouterClient

            self.llm_provider = OpenRouterClient(self._observer_cfg)
        elif self._provider_name == "mcp_gateway":
            from .llm_providers import MCPGatewayClient

            self.llm_provider = MCPGatewayClient(self._observer_cfg)

    def route(self, tool_name: str, params: dict[str, Any]) -> str:
        """
        Determine routing for a tool request.

        Returns: "auto" | "approve" | "block"
        """
        # Try rules first (instant, no latency)
        decision = route_by_rules(
            tool_name,
            params,
            self.security_mode,
            self.whitelist,
            self.blacklist,
        )

        if decision is not None:
            self.logger.debug("Rule decision for %s: %s", tool_name, decision)
            return decision

        # LLM fallback for unknown tools
        self._init_llm_provider()
        if self.llm_provider and self.llm_provider.is_available():
            return self._llm_decide(tool_name, params)

        # Default to approval if no LLM
        self.logger.warning("No rule or LLM for %s, defaulting to approve", tool_name)
        return "approve"

    def _llm_decide(self, tool_name: str, params: dict[str, Any]) -> str:
        """Use LLM to decide on unknown tool."""
        prompt = (
            f"Tool: {tool_name}\n"
            f"Params: {params}\n"
            "Is this tool safe to auto-execute? Reply with one word: AUTO, APPROVE, or BLOCK"
        )

        try:
            response = self.llm_provider.complete(prompt).strip().upper()
            if "AUTO" in response:
                self.logger.info("LLM decided AUTO for %s", tool_name)
                return "auto"
            if "BLOCK" in response:
                self.logger.info("LLM decided BLOCK for %s", tool_name)
                return "block"
            self.logger.info("LLM decided APPROVE for %s", tool_name)
            return "approve"
        except Exception as e:
            self.logger.error("LLM fallback failed: %s", e)
            return "approve"
