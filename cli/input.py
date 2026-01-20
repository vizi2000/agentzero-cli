"""prompt_toolkit input handling with history for CLI mode."""

import os
from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings


class SlashCommandCompleter(Completer):
    """Completer for slash commands with descriptions."""

    def __init__(self):
        self.commands: dict[str, str] = {}

    def set_commands(self, commands: dict[str, tuple[Callable, str, list[str]]]) -> None:
        """Update available commands from CLISlashCommands registry."""
        self.commands = {name: desc for name, (_, desc, _) in commands.items()}

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        # Only complete after /
        if not text.startswith("/"):
            return

        # Get partial command (without /)
        partial = text[1:].lower()

        # Filter and sort matching commands
        matches = [(name, desc) for name, desc in self.commands.items() if name.startswith(partial)]
        matches.sort(key=lambda x: x[0])

        for name, desc in matches:
            yield Completion(
                name,
                start_position=-len(partial),
                display=f"/{name}",
                display_meta=desc,
            )


def _create_key_bindings() -> KeyBindings:
    """Create key bindings for slash command completion."""
    kb = KeyBindings()

    @kb.add("/")
    def _(event):
        """Insert / and trigger completion menu."""
        buf = event.app.current_buffer
        # Only trigger at start of line or after whitespace
        if buf.cursor_position == 0 or buf.text[buf.cursor_position - 1] in " \t":
            buf.insert_text("/")
            buf.start_completion(select_first=False)
        else:
            buf.insert_text("/")

    return kb


class InputHandler:
    """Handles user input with prompt_toolkit."""

    HISTORY_FILE = ".a0_cli_history"

    def __init__(self, workspace_root: str = "."):
        """Initialize input handler.

        Args:
            workspace_root: Directory for history file
        """
        history_path = os.path.join(workspace_root, self.HISTORY_FILE)
        self.history = FileHistory(history_path)
        self.completer = SlashCommandCompleter()
        self.key_bindings = _create_key_bindings()
        self.session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
            completer=self.completer,
            complete_while_typing=True,
            key_bindings=self.key_bindings,
        )

    def set_commands(self, commands: dict[str, tuple[Callable, str, list[str]]]) -> None:
        """Update completer with available commands."""
        self.completer.set_commands(commands)

    async def get_input(self, prompt: str = "> ") -> str:
        """Get single-line input from user.

        Args:
            prompt: Prompt string to display

        Returns:
            User input string (stripped)

        Raises:
            EOFError: On Ctrl+D
            KeyboardInterrupt: On Ctrl+C
        """
        result = await self.session.prompt_async(prompt)
        return result.strip() if result else ""

    def get_multiline(self) -> str:
        """Get multi-line input (for /ml command).

        User types multiple lines, empty line to finish.

        Returns:
            Multi-line input string
        """
        lines = []
        print("Enter multi-line input (empty line to finish):")
        try:
            while True:
                line = self.session.prompt("... ")
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)

    def get_approval(self) -> str:
        """Get tool approval input.

        Returns:
            Single character: 'a', 'r', or 'e'
        """
        while True:
            try:
                choice = input("[A]pprove / [R]eject / [E]xplain? ").strip().lower()
                if choice in ("a", "approve", "y", "yes"):
                    return "a"
                if choice in ("r", "reject", "n", "no"):
                    return "r"
                if choice in ("e", "explain"):
                    return "e"
                print("Enter A, R, or E")
            except (EOFError, KeyboardInterrupt):
                return "r"
