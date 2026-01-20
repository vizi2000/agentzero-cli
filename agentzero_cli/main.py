#!/usr/bin/env python3
"""AgentZero CLI - TUI entry point.

Usage:
    a0          # Main command
    a0tui       # Alias
    agentzero   # Full name
"""

import os
import sys


def main():
    """Run the AgentZero TUI application."""
    from .logging_config import setup_logging
    setup_logging()

    from rich.console import Console
    from .cli.setup_wizard import check_and_run_wizard, config_exists

    if not config_exists():
        console = Console()
        config_path = check_and_run_wizard(console)
        if config_path is None:
            console.print("[red]Configuration required. Exiting.[/]")
            sys.exit(1)
        console.print("[green]Starting Agent Zero TUI...[/]")

    from .ui.app import AgentZeroCLI

    app = AgentZeroCLI()
    app.run()


if __name__ == "__main__":
    main()
