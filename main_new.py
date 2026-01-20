#!/usr/bin/env python3
"""AgentZeroCLI - TUI operator panel for Agent Zero remote control.

This is the entry point for the application.
"""

import os
import sys

from logging_config import setup_logging

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console

from cli.setup_wizard import check_and_run_wizard, config_exists


def main():
    """Run the AgentZeroCLI application."""
    setup_logging()

    if not config_exists():
        console = Console()
        config_path = check_and_run_wizard(console)
        if config_path is None:
            console.print("[red]Configuration required. Exiting.[/]")
            sys.exit(1)
        console.print("[green]Starting Agent Zero TUI...[/]")

    from ui.app import AgentZeroCLI

    app = AgentZeroCLI()
    app.run()


if __name__ == "__main__":
    main()
