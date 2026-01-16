"""Slash command registry and handlers for CLI mode."""

import shlex
from collections.abc import Callable
from typing import Any

from rich.prompt import Prompt
from rich.table import Table


class CLISlashCommands:
    """Registry and executor for CLI slash commands."""

    def __init__(self):
        """Initialize with default commands."""
        self.commands: dict[str, tuple[Callable, str, list[str]]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in commands."""
        self.register("help", self._cmd_help, "Show available commands", [])
        self.register("quit", self._cmd_quit, "Exit CLI", [])
        self.register("exit", self._cmd_quit, "Exit CLI", [])
        self.register("clear", self._cmd_clear, "Clear screen", [])
        self.register("status", self._cmd_status, "Show connection status", [])
        self.register("mode", self._cmd_mode, "Change security mode", ["mode?"])
        self.register("security", self._cmd_security, "Security settings menu", [])
        self.register("ml", self._cmd_multiline, "Enter multi-line input mode", [])
        self.register("context", self._cmd_context, "Show context info", [])
        self.register("observer", self._cmd_observer, "Observer status", ["info?"])
        self.register("ai_observer", self._cmd_ai, "AI/LLM settings menu", [])

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        args: list[str],
    ) -> None:
        """Register a slash command."""
        self.commands[name.lower()] = (handler, description, args)

    def parse(self, text: str) -> tuple[str, list[str]] | None:
        """Parse slash command from text.

        Returns:
            (command_name, args) or None if not a slash command
        """
        text = text.strip()
        if not text.startswith("/"):
            return None
        try:
            parts = shlex.split(text[1:])
        except ValueError:
            parts = text[1:].split()
        if not parts:
            return None
        return parts[0].lower(), parts[1:]

    async def execute(self, app: Any, text: str) -> bool:
        """Execute slash command if present.

        Returns:
            True if command was handled, False otherwise
        """
        result = self.parse(text)
        if not result:
            return False

        cmd, args = result
        if cmd not in self.commands:
            app.renderer.error(f"Unknown command: /{cmd}. Type /help for list.")
            return True

        handler, _, _ = self.commands[cmd]
        try:
            await handler(app, args)
        except Exception as e:
            app.renderer.error(f"Command error: {e}")
        return True

    def get_help_text(self) -> str:
        """Get formatted help text."""
        lines = ["Available commands:"]
        for name, (_, desc, cmd_args) in sorted(self.commands.items()):
            arg_str = " ".join(f"<{a}>" for a in cmd_args) if cmd_args else ""
            lines.append(f"  /{name} {arg_str} - {desc}")
        return "\n".join(lines)

    # Command handlers

    async def _cmd_help(self, app: Any, args: list[str]) -> None:
        """Show help text."""
        app.renderer.info(self.get_help_text())

    async def _cmd_quit(self, app: Any, args: list[str]) -> None:
        """Exit the application."""
        app.running = False
        app.renderer.goodbye()

    async def _cmd_clear(self, app: Any, args: list[str]) -> None:
        """Clear the screen."""
        app.console.clear()
        app.renderer.header(
            app.backend.api_url or "not configured",
            app.backend.project_name,
            app.backend.security_mode,
        )

    async def _cmd_status(self, app: Any, args: list[str]) -> None:
        """Show connection status."""
        backend = app.backend
        status = (
            f"Connection Status:\n"
            f"  API: {backend.api_url or 'not configured'}\n"
            f"  Stream: {'on' if backend.stream_enabled else 'off'}\n"
            f"  Security: {backend.security_mode}\n"
            f"  Project: {backend.project_name}\n"
            f"  Agent: {backend.agent_profile_name}\n"
            f"  Context ID: {backend.context_id or 'none'}"
        )
        app.renderer.info(status)

    async def _cmd_mode(self, app: Any, args: list[str]) -> None:
        """Change security mode."""
        modes = ["paranoid", "balanced", "god_mode"]
        current = app.backend.security_mode

        if not args:
            # Interactive selection
            table = Table(title="Security Modes", show_header=False, box=None)
            table.add_column("Key", style="cyan bold")
            table.add_column("Mode", style="white")
            table.add_column("Description")
            table.add_row(
                "1",
                "paranoid" + (" ←" if current == "paranoid" else ""),
                "Approval for everything",
            )
            table.add_row(
                "2",
                "balanced" + (" ←" if current == "balanced" else ""),
                "Auto read, approval for write",
            )
            table.add_row(
                "3",
                "god_mode" + (" ←" if current == "god_mode" else ""),
                "Full auto (no approvals)",
            )
            app.console.print(table)

            choice = Prompt.ask("Select mode", choices=["1", "2", "3", "q"], default="q")
            if choice == "q":
                return
            mode = modes[int(choice) - 1]
        else:
            mode = args[0].lower()
            if mode not in modes:
                app.renderer.error("Mode must be: paranoid, balanced, or god_mode")
                return

        # Update backend
        app.backend.security_mode = mode

        # Save to config
        if "security" not in app.config:
            app.config["security"] = {}
        app.config["security"]["mode"] = mode
        from .app import save_config

        save_config(app.config, app.config_path)

        app.renderer.info(f"Security mode: {mode} [saved]")

    async def _cmd_security(self, app: Any, args: list[str]) -> None:
        """Interactive security settings menu."""
        while True:
            current_mode = app.backend.security_mode
            allow_shell = app.backend.allow_shell

            # Build table
            table = Table(title="Security Settings", box=None)
            table.add_column("Option", style="cyan bold")
            table.add_column("Setting", style="white")
            table.add_column("Value", style="green" if allow_shell else "yellow")
            table.add_row("1", "Security Mode", current_mode)
            table.add_row("2", "Allow Shell", "ON" if allow_shell else "OFF")
            table.add_row("", "", "")
            table.add_row("q", "Back", "")
            app.console.print(table)

            choice = Prompt.ask("Select option", choices=["1", "2", "q"], default="q")

            if choice == "q":
                break
            elif choice == "1":
                await self._cmd_mode(app, [])
            elif choice == "2":
                # Toggle shell
                new_value = not allow_shell
                app.backend.allow_shell = new_value

                # Save to config
                if "security" not in app.config:
                    app.config["security"] = {}
                app.config["security"]["allow_shell"] = new_value
                from .app import save_config

                save_config(app.config, app.config_path)

                status = "enabled" if new_value else "disabled"
                app.renderer.info(f"Shell: {status} [saved]")
                if new_value:
                    app.renderer.info("Warning: shell commands can run locally.")

    async def _cmd_multiline(self, app: Any, args: list[str]) -> None:
        """Enter multi-line input mode."""
        text = app.input_handler.get_multiline()
        if text.strip():
            await app.handle_message(text)

    async def _cmd_context(self, app: Any, args: list[str]) -> None:
        """Show context info."""
        backend = app.backend
        info = (
            f"Context Info:\n"
            f"  Enabled: {backend.context_enabled}\n"
            f"  Mode: {backend.context_mode}\n"
            f"  Signature: {backend._context_signature or 'none'}\n"
            f"  Max bytes: {backend.context_max_bytes}\n"
            f"  Max files: {backend.context_max_files}"
        )
        app.renderer.info(info)

    async def _cmd_observer(self, app: Any, args: list[str]) -> None:
        """Show observer configuration status."""
        if args and args[0] not in ("info", "status"):
            app.renderer.info("Usage: /observer [info|status]")
            return
        observer_config = app.config.get("observer", {})
        enabled = observer_config.get("enabled", False)
        mode = observer_config.get("mode", "automatic")
        provider = observer_config.get("provider", "openrouter")
        model = observer_config.get("model", "openai/gpt-4o-mini")
        app.renderer.info(
            f"Observer status:\n"
            f"  Enabled: {enabled}\n"
            f"  Mode: {mode}\n"
            f"  Provider: {provider}\n"
            f"  Model: {model}"
        )

    async def _cmd_ai(self, app: Any, args: list[str]) -> None:
        """Interactive AI/LLM settings menu."""
        while True:
            observer_config = app.config.get("observer", {})
            enabled = observer_config.get("enabled", False)
            provider = observer_config.get("provider", "openrouter")
            model = observer_config.get("model", "openai/gpt-4o-mini")
            has_openrouter_key = bool(observer_config.get("api_key"))
            has_mcp_key = bool(observer_config.get("mcp_api_key"))

            # Build table
            table = Table(title="AI / Observer Settings", box=None)
            table.add_column("Option", style="cyan bold")
            table.add_column("Setting", style="white")
            table.add_column("Value", style="green" if enabled else "yellow")

            status = "ON" if enabled else "OFF"
            table.add_row("1", "Observer", status)
            table.add_row("2", "Provider", provider)
            table.add_row("3", "Model", model)
            table.add_row("4", "Test LLM", "→ send test prompt")
            table.add_row("", "", "")
            key_status = (
                f"OpenRouter: {'✓' if has_openrouter_key else '✗'}  "
                f"MCP: {'✓' if has_mcp_key else '✗'}"
            )
            table.add_row("", "API Keys", key_status)
            table.add_row("", "", "")
            table.add_row("q", "Back", "")
            app.console.print(table)

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "q"], default="q")

            if choice == "q":
                break
            elif choice == "1":
                # Toggle observer
                new_value = not enabled
                if "observer" not in app.config:
                    app.config["observer"] = {}
                app.config["observer"]["enabled"] = new_value
                from .app import save_config

                save_config(app.config, app.config_path)
                status = "enabled" if new_value else "disabled"
                app.renderer.info(f"Observer: {status} [saved]")

            elif choice == "2":
                # Select provider
                table = Table(title="LLM Provider", show_header=False, box=None)
                table.add_column("Key", style="cyan bold")
                table.add_column("Provider", style="white")
                table.add_column("Status")
                table.add_row(
                    "1",
                    "openrouter" + (" ←" if provider == "openrouter" else ""),
                    "✓" if has_openrouter_key else "✗ no key",
                )
                table.add_row(
                    "2",
                    "mcp_gateway" + (" ←" if provider == "mcp_gateway" else ""),
                    "✓" if has_mcp_key else "✗ no key",
                )
                app.console.print(table)

                p_choice = Prompt.ask("Select provider", choices=["1", "2", "q"], default="q")
                if p_choice == "q":
                    continue
                new_provider = "openrouter" if p_choice == "1" else "mcp_gateway"
                if "observer" not in app.config:
                    app.config["observer"] = {}
                app.config["observer"]["provider"] = new_provider
                from .app import save_config

                save_config(app.config, app.config_path)
                app.renderer.info(f"Provider: {new_provider} [saved]")

            elif choice == "3":
                # Change model
                current = model
                app.console.print(f"[dim]Current model: {current}[/]")
                app.console.print(
                    "[dim]Examples: openai/gpt-4o-mini, anthropic/claude-3-haiku, "
                    "mistralai/mistral-7b-instruct[/]"
                )
                new_model = Prompt.ask("Enter model name", default=current)
                if new_model and new_model != current:
                    if "observer" not in app.config:
                        app.config["observer"] = {}
                    app.config["observer"]["model"] = new_model
                    from .app import save_config

                    save_config(app.config, app.config_path)
                    app.renderer.info(f"Model: {new_model} [saved]")

            elif choice == "4":
                # Test LLM
                app.console.print("[dim]Testing LLM connection...[/]")
                try:
                    if provider == "openrouter":
                        from llm_providers import OpenRouterClient

                        client = OpenRouterClient(observer_config)
                    else:
                        from llm_providers import MCPGatewayClient

                        client = MCPGatewayClient(observer_config)

                    if not client.is_available():
                        app.renderer.error(f"No API key for {provider}")
                        continue

                    result = client.complete("Say 'LLM test OK' in exactly 3 words")
                    if result:
                        app.renderer.info(f"LLM response: {result}")
                    else:
                        app.renderer.error("Empty response from LLM")
                except Exception as e:
                    app.renderer.error(f"LLM test failed: {e}")
