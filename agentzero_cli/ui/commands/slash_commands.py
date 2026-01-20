"""Slash command parser and executor for AgentZeroCLI."""

import shlex
from collections.abc import Callable
from typing import Any


class SlashCommandRegistry:
    """Registry for slash commands like /theme, /project, /clear."""

    def __init__(self):
        self.commands: dict[str, tuple[Callable, str, list[str]]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in commands."""
        self.register("theme", self._cmd_theme, "Switch theme", ["name"])
        self.register("project", self._cmd_project, "Switch project", ["name"])
        self.register("agent", self._cmd_agent, "Switch agent profile", ["name"])
        self.register("clear", self._cmd_clear, "Clear current chat", [])
        self.register("help", self._cmd_help, "Show available commands", [])
        self.register("new", self._cmd_new_tab, "Create new chat tab", ["name?"])
        self.register("close", self._cmd_close_tab, "Close current tab", [])
        self.register("upload", self._cmd_upload, "Upload file to workspace", ["path?"])
        self.register("status", self._cmd_status, "Show connection status", [])
        self.register("rename", self._cmd_rename, "Rename current chat tab", ["name"])
        self.register("observer", self._cmd_observer, "Observer status & menu", ["info?"])

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        args: list[str],
    ) -> None:
        """Register a new slash command."""
        self.commands[name.lower()] = (handler, description, args)

    def parse(self, text: str) -> tuple[str, list[str]] | None:
        """Parse slash command from text.

        Returns (command_name, args) or None if not a slash command.
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

        Returns True if command was handled, False otherwise.
        """
        result = self.parse(text)
        if not result:
            return False

        cmd, args = result
        if cmd not in self.commands:
            app.notify(f"Unknown command: /{cmd}. Type /help for list.", severity="warning")
            return True

        handler, _, _ = self.commands[cmd]
        try:
            await handler(app, args)
        except Exception as e:
            app.notify(f"Command error: {e}", severity="error")
        return True

    def get_suggestions(self, prefix: str) -> list[str]:
        """Get command suggestions for autocomplete."""
        if not prefix.startswith("/"):
            return []
        partial = prefix[1:].lower()
        return [f"/{cmd}" for cmd in self.commands if cmd.startswith(partial)]

    def get_help_text(self) -> str:
        """Get formatted help text for all commands."""
        lines = ["Available commands:"]
        for name, (_, desc, cmd_args) in sorted(self.commands.items()):
            arg_str = " ".join(f"<{a}>" for a in cmd_args) if cmd_args else ""
            lines.append(f"  /{name} {arg_str} - {desc}")
        return "\n".join(lines)

    # Command handlers
    async def _cmd_theme(self, app: Any, args: list[str]) -> None:
        if args:
            theme_name = " ".join(args)
            app.action_switch_theme(theme_name)
        else:
            from .ui.themes import THEME_PRESETS

            themes = ", ".join(THEME_PRESETS.keys())
            app.notify(f"Usage: /theme <name>\nAvailable: {themes}")

    async def _cmd_project(self, app: Any, args: list[str]) -> None:
        if args:
            app.action_switch_project(args[0])
        else:
            projects = ", ".join(app.projects.keys())
            app.notify(f"Usage: /project <name>\nAvailable: {projects}")

    async def _cmd_agent(self, app: Any, args: list[str]) -> None:
        if args:
            app.action_switch_agent_profile(args[0])
        else:
            profiles = ", ".join(app.agent_profiles.keys())
            app.notify(f"Usage: /agent <name>\nAvailable: {profiles}")

    async def _cmd_clear(self, app: Any, args: list[str]) -> None:
        session = app.session_manager.get_active()
        if session:
            session.clear()
            container = app.get_active_chat_container()
            if container:
                await container.remove_children()
            app.notify("Chat cleared")

    async def _cmd_help(self, app: Any, args: list[str]) -> None:
        app.notify(self.get_help_text())

    async def _cmd_new_tab(self, app: Any, args: list[str]) -> None:
        name = " ".join(args) if args else None
        app.create_new_chat_tab(name)

    async def _cmd_close_tab(self, app: Any, args: list[str]) -> None:
        app.close_current_chat_tab()

    async def _cmd_upload(self, app: Any, args: list[str]) -> None:
        if args:
            path = " ".join(args)
            await app.upload_file(path)
        else:
            await app.action_show_file_upload()

    async def _cmd_status(self, app: Any, args: list[str]) -> None:
        connection = app.active_config.get("connection", {})
        api_url = connection.get("api_url", "not configured")
        stream = "on" if connection.get("stream", False) else "off"
        mode = app.active_config.get("security", {}).get("mode", "balanced")
        status = (
            f"Connection Status:\n"
            f"  API: {api_url}\n"
            f"  Stream: {stream}\n"
            f"  Security: {mode}\n"
            f"  Project: {app.current_project}\n"
            f"  Agent: {app.current_profile}"
        )
        app.notify(status)

    async def _cmd_rename(self, app: Any, args: list[str]) -> None:
        if args:
            new_name = " ".join(args)
            session = app.session_manager.get_active()
            if session:
                app.session_manager.rename_session(session.id, new_name)
                app.notify(f"Chat renamed to: {new_name}")
        else:
            app.notify("Usage: /rename <new name>")

    async def _cmd_observer(self, app: Any, args: list[str]) -> None:
        """Show observer status or open the observer configuration screen."""
        observer_config = app.active_config.get("observer", {})
        if args and args[0] in ("info", "status"):
            enabled = observer_config.get("enabled", False)
            mode = observer_config.get("mode", "automatic")
            provider = observer_config.get("provider", observer_config.get("type", "agent_zero"))
            model = observer_config.get("model", "not configured")
            app.notify(
                f"Observer status:\n"
                f"  Enabled: {enabled}\n"
                f"  Mode: {mode}\n"
                f"  Provider: {provider}\n"
                f"  Model: {model}"
            )
            return
        await app.action_show_observer_settings()
