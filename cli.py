#!/usr/bin/env python3
"""AgentZeroCLI - CLI interface for Agent Zero remote control.

This is the entry point for the CLI (non-TUI) version.
Similar to Claude Code in look and feel.

Usage:
    python cli.py
    ./a0 --cli
"""

import asyncio
import os
import sys

from logging_config import setup_logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.app import CLIApp


def main():
    """Run the AgentZeroCLI CLI application."""
    setup_logging()
    app = CLIApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
