"""First-run setup wizard for AgentZeroCLI.

Prompts user for essential configuration on first run.
Creates config.yaml with minimal required settings.
"""

from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt


def get_config_path() -> Path:
    """Get config file path.

    Priority:
    1. ./config.yaml (current directory)
    2. ~/.config/agentzero/config.yaml (XDG standard)

    Returns:
        Path to config file
    """
    local_config = Path("config.yaml")
    if local_config.exists():
        return local_config

    xdg_config = Path.home() / ".config" / "agentzero" / "config.yaml"
    if xdg_config.exists():
        return xdg_config

    return xdg_config


def config_exists() -> bool:
    """Check if any config file exists."""
    local_config = Path("config.yaml")
    xdg_config = Path.home() / ".config" / "agentzero" / "config.yaml"
    return local_config.exists() or xdg_config.exists()


def create_minimal_config(
    api_url: str,
    api_key: str,
    security_mode: str = "balanced",
    observer_config: dict | None = None,
) -> dict:
    """Create minimal working configuration.

    Args:
        api_url: Agent Zero API URL
        api_key: Agent Zero API key
        security_mode: Security mode (paranoid/balanced/god_mode)
        observer_config: Optional Observer configuration

    Returns:
        Config dictionary
    """
    config = {
        "connection": {
            "api_url": api_url,
            "api_key": api_key,
            "ui_url": api_url.replace("/api_message", "/"),
            "timeout_seconds": 0,
            "workspace_root": ".",
            "stream": True,
        },
        "security": {
            "mode": security_mode,
            "allow_shell": security_mode == "god_mode",
            "whitelist": ["ls", "cat", "git status", "pwd"],
            "blacklist_patterns": ["rm -rf", "format", "mkfs", "shutdown"],
        },
        "ui": {
            "theme": "Studio Dark",
            "waiting_game": "invaders",
        },
        "observer": observer_config or {"enabled": False},
    }
    return config


def setup_observer(console: Console) -> dict | None:
    """Setup Observer configuration interactively.

    Args:
        console: Rich console for output

    Returns:
        Observer config dict or None if skipped
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]AI Observer Setup (Optional)[/]\n\n"
            "The Observer is an AI layer that can help route tools,\n"
            "provide context, and enhance Agent Zero's capabilities.",
            border_style="cyan",
        )
    )
    console.print()

    if not Confirm.ask("[bold]Enable AI Observer?[/]", default=False):
        return {"enabled": False}

    console.print()
    console.print("[bold]Observer Provider:[/]")
    console.print("  [cyan]1[/] - OpenRouter (cloud, many models)")
    console.print("  [cyan]2[/] - Local Ollama (local, private)")
    console.print("  [cyan]3[/] - MCP Gateway (custom endpoint)")
    console.print()

    provider_choice = Prompt.ask(
        "[bold]Select provider[/]",
        choices=["1", "2", "3"],
        default="1",
    )

    observer_config = {"enabled": True, "mode": "automatic"}

    if provider_choice == "1":
        observer_config["provider"] = "openrouter"
        console.print()
        console.print("[dim]Get your OpenRouter API key from https://openrouter.ai/keys[/]")
        api_key = Prompt.ask("[bold]OpenRouter API Key[/]")
        if api_key:
            observer_config["api_key"] = api_key
            observer_config["model"] = Prompt.ask(
                "[bold]Model[/]",
                default="anthropic/claude-3-haiku",
            )
        else:
            console.print("[yellow]No API key provided, Observer disabled.[/]")
            return {"enabled": False}

    elif provider_choice == "2":
        observer_config["provider"] = "local"
        console.print()
        console.print("[dim]Ollama endpoint, e.g., http://localhost:11434[/]")
        endpoint = Prompt.ask(
            "[bold]Ollama endpoint[/]",
            default="http://localhost:11434",
        )
        observer_config["endpoint"] = endpoint
        observer_config["model"] = Prompt.ask(
            "[bold]Model name[/]",
            default="llama3.2",
        )

    elif provider_choice == "3":
        observer_config["provider"] = "mcp_gateway"
        console.print()
        console.print("[dim]MCP Gateway endpoint URL[/]")
        endpoint = Prompt.ask("[bold]MCP Gateway URL[/]")
        if endpoint:
            observer_config["endpoint"] = endpoint
            api_key = Prompt.ask("[bold]MCP Gateway API Key (optional)[/]", default="")
            if api_key:
                observer_config["api_key"] = api_key
        else:
            console.print("[yellow]No endpoint provided, Observer disabled.[/]")
            return {"enabled": False}

    console.print()
    console.print(f"[green]Observer configured: {observer_config['provider']}[/]")
    return observer_config


def save_config(config: dict, path: Path) -> None:
    """Save config to file.

    Args:
        config: Config dictionary
        path: Path to save config file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_setup_wizard(console: Console | None = None) -> Path | None:
    """Run interactive setup wizard.

    Prompts user for essential configuration.

    Args:
        console: Rich console for output (creates new one if None)

    Returns:
        Path to created config file, or None if cancelled
    """
    if console is None:
        console = Console()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Agent Zero CLI - First Run Setup[/]\n\n"
            "No configuration found. Let's set up your connection to Agent Zero.",
            border_style="cyan",
        )
    )
    console.print()

    console.print("[dim]Agent Zero API URL format: http://host:port/api_message[/]")
    console.print("[dim]Example: http://localhost:50001/api_message[/]")
    console.print()

    api_url = Prompt.ask(
        "[bold]Agent Zero API URL[/]",
        default="http://localhost:50001/api_message",
    )

    if not api_url:
        console.print("[yellow]Setup cancelled.[/]")
        return None

    console.print()
    console.print("[dim]API key is required for authentication.[/]")
    console.print("[dim]Get it from your Agent Zero server configuration.[/]")
    console.print()

    api_key = Prompt.ask("[bold]API Key[/]")

    if not api_key:
        console.print("[yellow]API key is required. Setup cancelled.[/]")
        return None

    console.print()
    console.print("[bold]Security Mode:[/]")
    console.print("  [cyan]paranoid[/]  - Approve every action (safest)")
    console.print("  [green]balanced[/]  - Auto-approve reads, ask for writes (recommended)")
    console.print("  [red]god_mode[/]  - Auto-approve everything (use with caution)")
    console.print()

    security_mode = Prompt.ask(
        "[bold]Security mode[/]",
        choices=["paranoid", "balanced", "god_mode"],
        default="balanced",
    )

    console.print()
    console.print("[bold]Where to save config?[/]")
    console.print("  [cyan]1[/] - ~/.config/agentzero/config.yaml (recommended, global)")
    console.print("  [cyan]2[/] - ./config.yaml (current directory only)")
    console.print()

    location = Prompt.ask(
        "[bold]Config location[/]",
        choices=["1", "2"],
        default="1",
    )

    if location == "1":
        config_path = Path.home() / ".config" / "agentzero" / "config.yaml"
    else:
        config_path = Path("config.yaml")

    observer_config = setup_observer(console)

    config = create_minimal_config(api_url, api_key, security_mode, observer_config)

    console.print()
    console.print("[bold]Configuration Summary:[/]")
    console.print(f"  API URL: [cyan]{api_url}[/]")
    console.print(f"  API Key: [cyan]{'*' * 8}...{api_key[-4:] if len(api_key) > 4 else '****'}[/]")
    console.print(f"  Security: [cyan]{security_mode}[/]")
    if observer_config and observer_config.get("enabled"):
        console.print(f"  Observer: [cyan]{observer_config.get('provider', 'enabled')}[/]")
    else:
        console.print("  Observer: [dim]disabled[/]")
    console.print(f"  Config path: [cyan]{config_path}[/]")
    console.print()

    if not Confirm.ask("[bold]Save configuration?[/]", default=True):
        console.print("[yellow]Setup cancelled.[/]")
        return None

    save_config(config, config_path)

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]Configuration saved![/]\n\n"
            f"Config file: [cyan]{config_path}[/]\n\n"
            "You can edit this file later to add more options.\n"
            "See config.example.yaml for all available settings.",
            border_style="green",
        )
    )
    console.print()

    return config_path


def check_and_run_wizard(console: Console | None = None) -> Path | None:
    """Check if setup is needed and run wizard if so.

    Args:
        console: Rich console for output

    Returns:
        Path to config file (existing or newly created), or None if setup cancelled
    """
    if config_exists():
        return get_config_path()

    return run_setup_wizard(console)
