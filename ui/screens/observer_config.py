"""Observer configuration summary modal."""

from typing import Any

from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


def _format_config(config: dict[str, Any]) -> str:
    lines = ["Observer configuration"]
    enabled = config.get("enabled")
    lines.append(f"Enabled: {enabled}")
    lines.append(f"Type: {config.get('type', 'agent_zero')}")
    provider = config.get("provider", "agent_zero")
    lines.append(f"Provider: {provider}")
    if provider == "openai":
        lines.append(f"Model: {config.get('model', 'not set')}")
        lines.append("API key: set" if config.get("api_key") else "API key: missing")
    elif provider == "openrouter":
        lines.append(f"Model: {config.get('model', 'not set')}")
        lines.append(f"Endpoint: {config.get('endpoint', 'https://openrouter.ai')}")
    elif provider == "local":
        lines.append(f"Local model path: {config.get('path', 'not configured')}")
    lines.append("Observer always runs read-only and cannot execute tools.")
    lines.append("Use F5 (or /observer) to open Agent Zero web UI and see the live session.")
    return "\n".join(lines)


class ObserverConfigScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    DEFAULT_CSS = """
    ObserverConfigScreen {
        align: center middle;
        background: rgba(6, 8, 12, 0.95);
    }
    #observer-dialog {
        width: 70;
        height: auto;
        border: solid $primary;
        border-radius: 1;
        padding: 1;
        background: rgba($panel, 0.95);
        box-shadow: 0 10px 30px rgba($boost, 0.7);
    }
    #observer-header {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #observer-body {
        background: rgba($surface, 0.9);
        border-radius: 1;
        padding: 1;
        border: solid rgba($boost, 0.4);
    }
    #observer-buttons {
        margin-top: 1;
        align: center middle;
    }
    #observer-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: dict[str, Any], ui_url: str | None) -> None:  # type: ignore[valid-type]
        super().__init__()
        self.config = config or {}
        self.ui_url = ui_url

    def compose(self):
        content = _format_config(self.config)
        yield Static("Observer settings", id="observer-header")
        yield Static(content, id="observer-body")
        with Horizontal(id="observer-buttons"):
            yield Button("Close", id="close-btn", variant="primary")
            if self.ui_url:
                yield Button("Open Agent UI", id="open-btn", variant="success")
            yield Button("Edit config", id="edit-btn", variant="default")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "open-btn":
            self.dismiss("open_ui")
        elif event.button.id == "edit-btn":
            self.dismiss("edit_config")
