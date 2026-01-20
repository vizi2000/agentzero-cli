#!/usr/bin/env python3
"""AgentZero CLI - CLI (non-TUI) entry point.

Usage:
    a0cli       # CLI mode
"""

import asyncio
import sys


def main():
    """Run the AgentZero CLI application."""
    from .logging_config import setup_logging
    setup_logging()
    
    from .cli.app import CLIApp

    app = CLIApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
