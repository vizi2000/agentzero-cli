"""Base LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str:
        """Send completion request and return text response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass
