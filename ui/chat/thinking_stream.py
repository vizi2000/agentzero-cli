"""Widget for streaming agent thoughts/reasoning to chat."""

from textual.reactive import reactive
from textual.widgets import Static


class ThinkingStreamWidget(Static):
    """Collapsible widget for streaming agent thoughts.

    Shows the latest thought with option to expand and see all.
    Click to toggle expanded view.
    """

    is_expanded: reactive[bool] = reactive(False)

    PREVIEW_LENGTH = 80
    MAX_THOUGHTS = 50

    def __init__(self, **kwargs):
        super().__init__("", classes="thinking-stream", **kwargs)
        self._thoughts: list[str] = []

    def add_thought(self, thought: str) -> None:
        """Add a new thought to the stream."""
        if thought:
            self._thoughts.append(thought)
            if len(self._thoughts) > self.MAX_THOUGHTS:
                self._thoughts = self._thoughts[-self.MAX_THOUGHTS :]
            self._render()

    def _render(self) -> None:
        if not self._thoughts:
            self.update("")
            self.display = False
            return

        self.display = True

        if self.is_expanded:
            lines = [f"  {t}" for t in self._thoughts]
            content = "\n".join(lines)
            message = (
                f"[dim italic]Thinking ({len(self._thoughts)}):\n"
                f"{content}\n"
                "[Click to collapse][/]"
            )
            self.update(message)
        else:
            latest = self._thoughts[-1]
            preview = latest[: self.PREVIEW_LENGTH]
            if len(latest) > self.PREVIEW_LENGTH:
                preview += "..."
            count = f"({len(self._thoughts)})" if len(self._thoughts) > 1 else ""
            self.update(f"[dim italic]Thinking {count}: {preview} [Click to expand][/]")

    def on_click(self) -> None:
        self.is_expanded = not self.is_expanded
        self._render()

    def clear(self) -> None:
        self._thoughts.clear()
        self.is_expanded = False
        self._render()

    def get_thoughts(self) -> list[str]:
        return self._thoughts.copy()
