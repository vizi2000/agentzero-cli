"""Thinking indicator widgets for AgentZeroCLI."""

from textual.reactive import reactive
from textual.widgets import Static


class ThinkingIndicator(Static):
    """Animated thinking indicator for chat."""

    is_thinking: reactive[bool] = reactive(False)
    thinking_text: reactive[str] = reactive("")

    SPINNER_FRAMES = [".", "..", "...", "....", "...", ".."]

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self._frame = 0
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.2, self._update_spinner)
        self.display = False

    def _update_spinner(self) -> None:
        if self.is_thinking:
            self._frame = (self._frame + 1) % len(self.SPINNER_FRAMES)
            spinner = self.SPINNER_FRAMES[self._frame]
            text = self.thinking_text or "Agent is thinking"
            self.update(f"[italic]{text}{spinner}[/]")

    def start(self, message: str = "Agent is thinking") -> None:
        self.thinking_text = message
        self.is_thinking = True
        self.display = True
        self.set_class(True, "active")

    def stop(self) -> None:
        self.is_thinking = False
        self.display = False
        self.set_class(False, "active")


class BrandBarIndicator(Static):
    """Pulsing indicator for brand bar showing THINKING/READY state."""

    is_active: reactive[bool] = reactive(False)

    PULSES = ["", ".", "..", "..."]

    def __init__(self, **kwargs):
        super().__init__("READY", **kwargs)
        self._frame = 0
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.3, self._pulse)

    def _pulse(self) -> None:
        if self.is_active:
            self._frame = (self._frame + 1) % len(self.PULSES)
            self.update(f"THINKING{self.PULSES[self._frame]}")
        else:
            self.update("READY")

    def set_thinking(self, active: bool) -> None:
        self.is_active = active
        if not active:
            self.update("READY")
