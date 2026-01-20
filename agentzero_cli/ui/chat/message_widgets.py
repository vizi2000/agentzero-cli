"""Animated text widgets for chat messages."""

from textual.widgets import Markdown, Static


class AnimatedText(Static):
    """Static text that animates character by character."""

    def __init__(
        self,
        text: str,
        *,
        speed: float = 0.004,
        chunk_size: int = 10,
        max_chars: int = 3200,
        **kwargs,
    ):
        super().__init__("", **kwargs)
        self.full_text = text or ""
        self.speed = speed
        self.chunk_size = max(1, chunk_size)
        self.max_chars = max_chars
        self._index = 0
        self._timer = None

    def on_mount(self) -> None:
        if not self.full_text:
            return
        if len(self.full_text) > self.max_chars:
            self.update(self.full_text)
            return
        self._timer = self.set_interval(self.speed, self._tick)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        self._index = min(len(self.full_text), self._index + self.chunk_size)
        self.update(self.full_text[: self._index])
        self._scroll_chat()
        if self._index >= len(self.full_text) and self._timer:
            self._timer.stop()
            self._timer = None

    def _scroll_chat(self) -> None:
        try:
            self.app.query_one("#chat-container").scroll_end()
        except Exception:
            pass


class AnimatedMarkdown(Markdown):
    """Markdown widget that animates character by character."""

    def __init__(
        self,
        text: str,
        *,
        speed: float = 0.012,
        chunk_size: int = 8,
        max_chars: int = 3200,
        **kwargs,
    ):
        super().__init__("", **kwargs)
        self.full_text = text or ""
        self.speed = speed
        self.chunk_size = max(1, chunk_size)
        self.max_chars = max_chars
        self._index = 0
        self._timer = None

    def on_mount(self) -> None:
        if not self.full_text:
            return
        if len(self.full_text) > self.max_chars:
            self.update(self.full_text)
            return
        self._timer = self.set_interval(self.speed, self._tick)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        self._index = min(len(self.full_text), self._index + self.chunk_size)
        self.update(self.full_text[: self._index])
        self._scroll_chat()
        if self._index >= len(self.full_text) and self._timer:
            self._timer.stop()
            self._timer = None

    def _scroll_chat(self) -> None:
        try:
            self.app.query_one("#chat-container").scroll_end()
        except Exception:
            pass
