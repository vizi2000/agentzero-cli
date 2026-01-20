"""
AgentZero CLI - AI coding agent with security interceptor.

A TUI/CLI tool for AI-assisted coding with:
- Security interceptor blocking dangerous commands
- Multi-backend support (Local LLM, OpenRouter, etc.)
- Human-in-the-loop approval for tool execution
"""

__version__ = "0.2.0"
__author__ = "Wojciech Wiesner"

from .backend import get_backend

__all__ = ["get_backend", "__version__"]
