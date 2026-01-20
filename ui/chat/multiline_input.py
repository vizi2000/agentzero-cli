"""Multiline input widget with Enter to submit and Shift+Enter for newline."""

from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.widgets import TextArea


class MultilineInput(TextArea):
    """Multi-line input widget supporting paste of multiple lines.

    - Enter: Submit the message
    - Shift+Enter: Insert newline
    - Supports full paste of multi-line text
    """

    # Use priority bindings to intercept before default handling
    BINDINGS = [
        Binding("shift+enter", "newline", "Newline", show=False, priority=True),
    ]

    class Submitted(Message):
        """Posted when user submits input."""

        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def __init__(
        self,
        placeholder: str = "",
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(
            id=id,
            classes=classes,
            show_line_numbers=False,
            soft_wrap=True,
            tab_behavior="indent",
        )
        self._placeholder = placeholder

    def on_mount(self) -> None:
        self.border_title = self._placeholder

    def action_newline(self) -> None:
        """Insert a newline (Shift+Enter)."""
        self.insert("\n")

    def _on_key(self, event: Key) -> None:
        """Handle Enter key to submit - intercept before TextArea processes it."""
        # shift+enter is handled by binding, so if we get here with enter,
        # it's plain enter (or ctrl+m which is alias)
        if event.key == "enter" and "shift+enter" not in (event.key, event.name):
            # Prevent default TextArea behavior
            event.prevent_default()
            event.stop()
            # Submit if we have content
            value = self.text.strip()
            if value:
                self.post_message(self.Submitted(value))
                self.clear()
            return
        # Let parent handle other keys
        super()._on_key(event)
