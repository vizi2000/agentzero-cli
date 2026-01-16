import copy
import json
import random
from datetime import datetime

import yaml
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, RichLog, Static

# Importujemy nasz symulator backendu
from backend import MockAgentBackend, RemoteAgentBackend
from logging_config import setup_logging

# --- Ładowanie Konfiguracji ---
try:
    with open("config.yaml") as f:
        CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    CONFIG = {"security": {"mode": "balanced"}}  # Fallback

# --- STYLE CSS ---
CSS = """
/* Global shell */
Screen { background: $app-bg; color: $app-fg; }
Header { background: $app-panel; color: $primary; text-style: bold; }
Footer { background: $app-panel; color: $app-muted; }

/* --- Layout --- */
#app-body { height: 1fr; padding: 1; hatch: none; }
#brand-bar {
    height: 3;
    padding: 0 1;
    margin-bottom: 1;
    border: panel $app-border;
    background: $app-panel;
    align: left middle;
}
#brand-title { color: $primary; text-style: bold; width: 1fr; }
#brand-meta { color: $app-muted; text-style: dim; width: 1fr; text-align: center; }
#brand-signal { color: $secondary; text-style: bold; width: 12; text-align: right; }
#main-row { height: 1fr; }

/* --- Chat --- */
#chat-container {
    height: 1fr;
    width: 3fr;
    border: panel $app-border;
    background: $app-chat;
    padding: 1;
    margin-right: 1;
    scrollbar-color: $primary $app-panel;
}

#side-panel {
    width: 1fr;
    border: panel $app-border;
    background: $app-panel;
    padding: 1;
    scrollbar-color: $secondary $app-panel;
}

.panel {
    background: $app-card;
    border: panel $app-border;
    padding: 1;
    margin-bottom: 1;
}
.panel-title { color: $secondary; text-style: bold; margin-bottom: 1; }

#activity-card { height: 12; }
#activity-feed {
    height: 1fr;
    background: $app-surface;
    color: $app-fg;
    padding: 0 1;
    border: solid $app-border;
    scrollbar-color: $secondary $app-panel;
    text-style: dim;
}

#arcade-card { height: 12; }
#arcade-screen {
    height: 1fr;
    background: $app-surface;
    color: $primary;
    padding: 0 1;
    hatch: none;
    text-style: dim;
}
#arcade-screen.waiting { color: $primary; }
#arcade-screen.idle { color: $app-muted; }

.user-msg {
    color: $app-ink;
    background: $app-user-bg;
    padding: 1;
    margin-bottom: 1;
    text-align: right;
    width: 100%;
    border: round $app-user-border;
}
.agent-thought {
    color: $app-muted;
    text-style: italic;
    padding-left: 2;
    margin-bottom: 0;
}
.agent-msg {
    color: $app-fg;
    background: $app-agent-bg;
    border: round $app-border;
    padding: 1;
    margin-bottom: 1;
    width: 100%;
}
.tool-output {
    color: $app-fg;
    background: $app-tool-bg;
    padding: 1;
    margin: 0 1 1 1;
    border: round $app-border;
    text-style: dim;
}
.system-msg {
    color: $app-fg;
    background: $app-system-bg;
    padding: 1;
    margin-bottom: 1;
    border: round $app-border;
    text-style: dim;
}
.status-msg {
    color: $app-muted;
    padding: 0 1;
    margin-bottom: 1;
    text-style: dim;
}

Input {
    background: $app-surface;
    color: $app-fg;
    border: panel $app-border;
}
#input-area {
    height: 3;
    padding: 0 1;
    border: panel $app-border;
}
#input-area:focus {
    border: solid $app-focus;
}

/* --- Tool Preview --- */
#preview-container {
    height: 10;
    margin: 1 0;
}
#preview-box {
    background: $app-surface;
    color: $app-fg;
    padding: 1;
    border: solid $app-border;
}

/* --- Security Modal --- */
ToolApprovalScreen {
    align: center middle;
    background: rgba(6, 8, 12, 0.9);
}
#dialog {
    padding: 1;
    width: 78;
    height: auto;
    border: heavy $app-warning;
    background: $app-panel;
}
#risk-header {
    background: $app-warning;
    color: $app-ink;
    text-align: center;
    text-style: bold;
    padding: 1;
    width: 100%;
}
#command-box {
    background: $app-surface;
    color: $app-warning-fg;
    padding: 1;
    margin: 1 0;
    border: solid $app-border;
    text-align: center;
}
#buttons-layout {
    align: center bottom;
    height: auto;
    margin-top: 1;
    margin-bottom: 1;
}
Button {
    margin: 0 1;
    border: none;
}
Button.success {
    background: $app-success;
    color: $app-ink;
}
Button.warning {
    background: $app-warning;
    color: $app-ink;
}
Button.error {
    background: $app-error;
    color: $app-ink;
}
Button:focus {
    text-style: bold;
    border: wide $app-border;
}
.explanation-text {
    color: $app-warning-fg;
    padding: 1;
    margin-top: 1;
    border-top: dashed $app-border;
}

/* --- GAME SCREEN (Agent ZUSA: Poland Mission) --- */
RetroGameScreen {
    background: #050510;
    align: center middle;
}
#game-header {
    dock: top;
    height: 3;
    content-align: center middle;
    background: #111;
    color: #00ff41;
    text-style: bold;
    border-bottom: solid #333;
}

#game-board {
    layout: grid;
    grid-size: 5 6;
    grid-gutter: 1;
    width: auto;
    height: auto;
    border: heavy #444;
    background: #000;
    padding: 1;
}

.city-node {
    width: 18;
    height: 3;
    background: #111;
    color: #555;
    border: solid #333;
    content-align: center middle;
    text-align: center;
}
.city-node:hover { background: #222; }

/* Stany gry */
.evil-agi {
    background: #550000;
    color: #ffaaaa;
    border: double #ff0000;
    text-style: bold blink;
}

.secure {
    background: #002200;
    color: #00aa00;
    border: solid #005500;
}

.agent-here {
    background: #004400;
    color: #ffffff;
    border: thick #ffffff;
    text-style: bold;
}

.destroyed {
    background: #222;
    color: #444;
    border: none;
    text-style: strike;
}

/* --- Theme Accents --- */
.theme-atari-800xl #brand-bar { border: heavy $app-border; }
.theme-commodore-c64 #brand-bar { border: double $app-border; }
.theme-zx-spectrum #brand-bar { border: heavy $app-border; }
.theme-atari-st #brand-bar { border: tall $app-border; }
.theme-amiga-500 #brand-bar { border: wide $app-border; }

.theme-ms-dos-xt-pc Header,
.theme-ms-dos-xt-pc Footer { text-style: bold; }
.theme-ms-dos-xt-pc #chat-container,
.theme-ms-dos-xt-pc #side-panel,
.theme-ms-dos-xt-pc .panel { border: ascii $app-border; }
.theme-ms-dos-xt-pc #brand-bar { border: ascii $app-border; }
.theme-ms-dos-xt-pc #app-body { hatch: none; }

.theme-mac-one #app-body,
.theme-mac-classic #app-body,
.theme-mac-aqua #app-body { hatch: none; }
.theme-mac-one #chat-container,
.theme-mac-classic #chat-container,
.theme-mac-aqua #chat-container { border: solid $app-border; }
.theme-mac-one .panel,
.theme-mac-classic .panel,
.theme-mac-aqua .panel { border: solid $app-border; }
"""

DEFAULT_THEME = "Studio Light"
THEME_ALIASES = {
    "default": DEFAULT_THEME,
    "claude": "Studio Light",
    "gemini": "Studio Light",
    "studio light": "Studio Light",
    "studio-light": "Studio Light",
    "studio_light": "Studio Light",
    "studio dark": "Studio Dark",
    "studio-dark": "Studio Dark",
    "studio_dark": "Studio Dark",
    "hacker_green": "MS DOS XT PC",
    "hacker-green": "MS DOS XT PC",
}


def _theme_vars(**overrides: str) -> dict:
    base = {
        "app-success": "#22c55e",
        "app-error": "#ff5e5e",
    }
    for key, value in overrides.items():
        base[key.replace("_", "-")] = value
    return base


THEME_PRESETS = {
    "Studio Light": Theme(
        name="Studio Light",
        primary="#2563eb",
        secondary="#0ea5e9",
        warning="#f59e0b",
        error="#ef4444",
        success="#22c55e",
        accent="#2563eb",
        foreground="#0f172a",
        background="#f6f7fb",
        surface="#f8fafc",
        panel="#ffffff",
        boost="#e2e8f0",
        dark=False,
        variables=_theme_vars(
            app_bg="#f6f7fb",
            app_fg="#0f172a",
            app_muted="#64748b",
            app_panel="#ffffff",
            app_card="#ffffff",
            app_border="#e2e8f0",
            app_surface="#f8fafc",
            app_chat="#f8fafc",
            app_user_bg="#e0f2fe",
            app_user_border="#93c5fd",
            app_agent_bg="#ffffff",
            app_tool_bg="#f1f5f9",
            app_system_bg="#f8fafc",
            app_warning="#f59e0b",
            app_warning_fg="#0f172a",
            app_accent="#2563eb",
            app_ink="#0f172a",
            app_focus="#2563eb",
        ),
    ),
    "Studio Dark": Theme(
        name="Studio Dark",
        primary="#60a5fa",
        secondary="#34d399",
        warning="#f59e0b",
        error="#ef4444",
        success="#22c55e",
        accent="#60a5fa",
        foreground="#e5e7eb",
        background="#0b0d10",
        surface="#0f141a",
        panel="#111827",
        boost="#1f2937",
        dark=True,
        variables=_theme_vars(
            app_bg="#0b0d10",
            app_fg="#e5e7eb",
            app_muted="#9ca3af",
            app_panel="#111827",
            app_card="#111827",
            app_border="#1f2937",
            app_surface="#0f141a",
            app_chat="#0f141a",
            app_user_bg="#1e293b",
            app_user_border="#3b82f6",
            app_agent_bg="#111827",
            app_tool_bg="#0f172a",
            app_system_bg="#0b1220",
            app_warning="#f59e0b",
            app_warning_fg="#fef3c7",
            app_accent="#60a5fa",
            app_ink="#0b0d10",
            app_focus="#60a5fa",
        ),
    ),
    "High Tech 2026": Theme(
        name="High Tech 2026",
        primary="#7dd3fc",
        secondary="#34d399",
        warning="#f5a524",
        error="#ff5e5e",
        success="#22c55e",
        accent="#7dd3fc",
        foreground="#e5e7eb",
        background="#0b0d10",
        surface="#0f141a",
        panel="#111827",
        boost="#1f2937",
        dark=True,
        variables=_theme_vars(
            app_bg="#0b0d10",
            app_fg="#e5e7eb",
            app_muted="#9ca3af",
            app_panel="#111827",
            app_card="#111827",
            app_border="#1f2937",
            app_surface="#0f141a",
            app_chat="#0f141a",
            app_user_bg="#1e293b",
            app_user_border="#3b82f6",
            app_agent_bg="#111827",
            app_tool_bg="#0f172a",
            app_system_bg="#0b1220",
            app_warning="#f5a524",
            app_warning_fg="#fff3c4",
            app_accent="#7dd3fc",
            app_ink="#0b0d10",
            app_focus="#7dd3fc",
        ),
    ),
    "Atari 800XL": Theme(
        name="Atari 800XL",
        primary="#6aa0ff",
        secondary="#f3d34a",
        warning="#f3d34a",
        error="#ff7a7a",
        success="#5bd67a",
        accent="#6aa0ff",
        foreground="#e8f1ff",
        background="#13224f",
        surface="#142454",
        panel="#1b2f66",
        boost="#2b4180",
        dark=True,
        variables=_theme_vars(
            app_bg="#13224f",
            app_fg="#e8f1ff",
            app_muted="#a7b9e6",
            app_panel="#1b2f66",
            app_card="#20356f",
            app_border="#6aa0ff",
            app_surface="#142454",
            app_chat="#13224f",
            app_user_bg="#f3d34a",
            app_user_border="#caa72e",
            app_agent_bg="#182a5d",
            app_tool_bg="#1c2f63",
            app_system_bg="#1f346d",
            app_warning="#f3d34a",
            app_warning_fg="#1b1b1b",
            app_accent="#6aa0ff",
            app_ink="#14203b",
            app_focus="#f3d34a",
        ),
    ),
    "Commodore C64": Theme(
        name="Commodore C64",
        primary="#8b83e0",
        secondary="#a7e2ff",
        warning="#ffd166",
        error="#ff8a8a",
        success="#79e08d",
        accent="#8b83e0",
        foreground="#d6d1ff",
        background="#352879",
        surface="#2f236b",
        panel="#40318e",
        boost="#4b3aa4",
        dark=True,
        variables=_theme_vars(
            app_bg="#352879",
            app_fg="#d6d1ff",
            app_muted="#b3adf6",
            app_panel="#40318e",
            app_card="#463694",
            app_border="#8b83e0",
            app_surface="#2f236b",
            app_chat="#31246f",
            app_user_bg="#a7e2ff",
            app_user_border="#6db6e3",
            app_agent_bg="#2b215f",
            app_tool_bg="#3b2f86",
            app_system_bg="#3e318b",
            app_warning="#ffd166",
            app_warning_fg="#352879",
            app_accent="#8b83e0",
            app_ink="#261d53",
            app_focus="#ffd166",
        ),
    ),
    "ZX Spectrum": Theme(
        name="ZX Spectrum",
        primary="#ff005c",
        secondary="#00f0ff",
        warning="#ffd200",
        error="#ff5a5a",
        success="#4bdc7a",
        accent="#ff005c",
        foreground="#f2f2f2",
        background="#000000",
        surface="#090909",
        panel="#111111",
        boost="#1a1a1a",
        dark=True,
        variables=_theme_vars(
            app_bg="#000000",
            app_fg="#f2f2f2",
            app_muted="#c0c0c0",
            app_panel="#111111",
            app_card="#141414",
            app_border="#ff005c",
            app_surface="#090909",
            app_chat="#0b0b0b",
            app_user_bg="#00f0ff",
            app_user_border="#00a8b5",
            app_agent_bg="#111111",
            app_tool_bg="#141414",
            app_system_bg="#1a1a1a",
            app_warning="#ffd200",
            app_warning_fg="#000000",
            app_accent="#ff005c",
            app_ink="#000000",
            app_focus="#ffd200",
        ),
    ),
    "Atari ST": Theme(
        name="Atari ST",
        primary="#7cff9a",
        secondary="#f4b400",
        warning="#f4b400",
        error="#ff7a7a",
        success="#7cff9a",
        accent="#7cff9a",
        foreground="#d7f5e3",
        background="#1b1e1d",
        surface="#1f2322",
        panel="#232726",
        boost="#2a2f2d",
        dark=True,
        variables=_theme_vars(
            app_bg="#1b1e1d",
            app_fg="#d7f5e3",
            app_muted="#96b6a6",
            app_panel="#232726",
            app_card="#2a2f2d",
            app_border="#7cff9a",
            app_surface="#1f2322",
            app_chat="#1b1e1d",
            app_user_bg="#7cff9a",
            app_user_border="#52c870",
            app_agent_bg="#222625",
            app_tool_bg="#272d2b",
            app_system_bg="#29302d",
            app_warning="#f4b400",
            app_warning_fg="#1b1e1d",
            app_accent="#7cff9a",
            app_ink="#14201a",
            app_focus="#f4b400",
        ),
    ),
    "Amiga 500": Theme(
        name="Amiga 500",
        primary="#7aa2ff",
        secondary="#ff8fb1",
        warning="#ff8fb1",
        error="#ff6f7f",
        success="#7aa2ff",
        accent="#7aa2ff",
        foreground="#f4ead7",
        background="#0e1028",
        surface="#141838",
        panel="#171a3a",
        boost="#1c2148",
        dark=True,
        variables=_theme_vars(
            app_bg="#0e1028",
            app_fg="#f4ead7",
            app_muted="#b7b1a6",
            app_panel="#171a3a",
            app_card="#1c2148",
            app_border="#7aa2ff",
            app_surface="#141838",
            app_chat="#11142e",
            app_user_bg="#f4ead7",
            app_user_border="#d2c6b2",
            app_agent_bg="#15193a",
            app_tool_bg="#1b2046",
            app_system_bg="#1c2148",
            app_warning="#ff8fb1",
            app_warning_fg="#2a1730",
            app_accent="#7aa2ff",
            app_ink="#2a2232",
            app_focus="#ff8fb1",
        ),
    ),
    "MS DOS XT PC": Theme(
        name="MS DOS XT PC",
        primary="#00ff66",
        secondary="#00ff66",
        warning="#00ff66",
        error="#00ff66",
        success="#00ff66",
        accent="#00ff66",
        foreground="#00ff66",
        background="#000000",
        surface="#000000",
        panel="#001106",
        boost="#001a0a",
        dark=True,
        variables=_theme_vars(
            app_bg="#000000",
            app_fg="#00ff66",
            app_muted="#00aa44",
            app_panel="#001106",
            app_card="#001408",
            app_border="#00ff66",
            app_surface="#000000",
            app_chat="#000000",
            app_user_bg="#00ff66",
            app_user_border="#00b94a",
            app_agent_bg="#000000",
            app_tool_bg="#001106",
            app_system_bg="#001106",
            app_warning="#00ff66",
            app_warning_fg="#000000",
            app_accent="#00ff66",
            app_ink="#000000",
            app_focus="#00ff66",
        ),
    ),
    "Mac One": Theme(
        name="Mac One",
        primary="#1d1d1d",
        secondary="#3d4c5b",
        warning="#1d1d1d",
        error="#1d1d1d",
        success="#1d1d1d",
        accent="#1d1d1d",
        foreground="#1d1d1d",
        background="#f2e8d5",
        surface="#f6efdf",
        panel="#e5d9c6",
        boost="#d6c9b4",
        dark=False,
        variables=_theme_vars(
            app_bg="#f2e8d5",
            app_fg="#1d1d1d",
            app_muted="#6b6b6b",
            app_panel="#e5d9c6",
            app_card="#eadfcd",
            app_border="#1d1d1d",
            app_surface="#f6efdf",
            app_chat="#f7f1e3",
            app_user_bg="#2b2b2b",
            app_user_border="#000000",
            app_agent_bg="#f6efdf",
            app_tool_bg="#e7dcc9",
            app_system_bg="#e0d5c1",
            app_warning="#1d1d1d",
            app_warning_fg="#f2e8d5",
            app_accent="#1d1d1d",
            app_ink="#f2e8d5",
            app_focus="#1d1d1d",
        ),
    ),
    "Mac Classic": Theme(
        name="Mac Classic",
        primary="#1a1a1a",
        secondary="#3a3a3a",
        warning="#1a1a1a",
        error="#1a1a1a",
        success="#1a1a1a",
        accent="#1a1a1a",
        foreground="#1a1a1a",
        background="#d6d6d6",
        surface="#e0e0e0",
        panel="#c9c9c9",
        boost="#bdbdbd",
        dark=False,
        variables=_theme_vars(
            app_bg="#d6d6d6",
            app_fg="#1a1a1a",
            app_muted="#6a6a6a",
            app_panel="#c9c9c9",
            app_card="#d0d0d0",
            app_border="#1a1a1a",
            app_surface="#e0e0e0",
            app_chat="#e7e7e7",
            app_user_bg="#1a1a1a",
            app_user_border="#000000",
            app_agent_bg="#e7e7e7",
            app_tool_bg="#d0d0d0",
            app_system_bg="#c5c5c5",
            app_warning="#1a1a1a",
            app_warning_fg="#d6d6d6",
            app_accent="#1a1a1a",
            app_ink="#f5f5f5",
            app_focus="#1a1a1a",
        ),
    ),
    "Mac Aqua": Theme(
        name="Mac Aqua",
        primary="#2f7fd6",
        secondary="#5aa8ff",
        warning="#f5a524",
        error="#ff6b6b",
        success="#4fa87a",
        accent="#2f7fd6",
        foreground="#1a2a3a",
        background="#e8f0f8",
        surface="#f1f6fb",
        panel="#f5f7fb",
        boost="#d9e6f3",
        dark=False,
        variables=_theme_vars(
            app_bg="#e8f0f8",
            app_fg="#1a2a3a",
            app_muted="#5f6f82",
            app_panel="#f5f7fb",
            app_card="#eef3f8",
            app_border="#5aa8ff",
            app_surface="#f1f6fb",
            app_chat="#f7fbff",
            app_user_bg="#5aa8ff",
            app_user_border="#2f7fd6",
            app_agent_bg="#f1f6fb",
            app_tool_bg="#e5edf5",
            app_system_bg="#e0e8f0",
            app_warning="#f5a524",
            app_warning_fg="#1a2a3a",
            app_accent="#2f7fd6",
            app_ink="#f7fbff",
            app_focus="#2f7fd6",
        ),
    ),
}


def _slugify_theme(name: str) -> str:
    cleaned = []
    last_dash = False
    for char in name.lower().strip():
        if char.isalnum():
            cleaned.append(char)
            last_dash = False
        else:
            if not last_dash:
                cleaned.append("-")
                last_dash = True
    return "".join(cleaned).strip("-")


# --- Animated text helpers ---
class AnimatedText(Static):
    def __init__(
        self,
        text: str,
        *,
        speed: float = 0.01,
        chunk_size: int = 6,
        max_chars: int = 2400,
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


class ArcadeWidget(Static):
    def __init__(self, mode: str = "invaders", fps: int = 12, **kwargs):
        super().__init__("", **kwargs)
        self.mode = mode
        self.fps = fps
        self.active = False
        self._timer = None
        self._frame = 0
        self._rng = random.Random()
        self._stars = []
        self._board_width = 0
        self._board_height = 0
        self._invaders = set()
        self._invader_rows = 0
        self._invader_cols = 0
        self._invader_origin_x = 0
        self._invader_origin_y = 0
        self._invader_dir = 1
        self._invader_speed = 3
        self._player_x = 0
        self._bullet = None
        self._pong_ball = [0, 0]
        self._pong_dir = [1, 1]
        self._pong_left_y = 0
        self._pong_right_y = 0
        self._pong_paddle = 3

    def on_mount(self) -> None:
        self._sync_board()
        self._reset_state()
        self._render_idle()

    def on_resize(self, event) -> None:
        self._sync_board()
        self._reset_state()
        if self.active:
            self._render_frame()
        else:
            self._render_idle()

    def set_mode(self, mode: str) -> None:
        if mode not in ("invaders", "pong", "off"):
            mode = "invaders"
        self.mode = mode
        self._reset_state()
        if self.active:
            self._render_frame()
        else:
            if self.mode == "off":
                self._render_off()
            else:
                self._render_idle()

    def start(self) -> None:
        if self.mode == "off":
            self.active = False
            self.set_class(True, "idle")
            self.set_class(False, "waiting")
            if self._timer:
                self._timer.stop()
                self._timer = None
            self._render_off()
            return
        self.active = True
        self.set_class(True, "waiting")
        self.set_class(False, "idle")
        if self._timer is None:
            self._timer = self.set_interval(1 / max(1, self.fps), self._tick)
        self._render_frame()

    def stop(self) -> None:
        self.active = False
        self.set_class(True, "idle")
        self.set_class(False, "waiting")
        if self._timer:
            self._timer.stop()
            self._timer = None
        if self.mode == "off":
            self._render_off()
        else:
            self._render_idle()

    def _sync_board(self) -> None:
        width = self.size.width or 28
        height = self.size.height or 10
        self._board_width = max(18, width)
        self._board_height = max(8, height)

    def _reset_state(self) -> None:
        self._frame = 0
        self._stars = []
        if self.mode == "pong":
            self._reset_pong()
        else:
            self._reset_invaders()

    def _reset_invaders(self) -> None:
        width = self._board_width
        self._invader_cols = max(4, min(9, (width - 6) // 3))
        self._invader_rows = 3
        self._invader_origin_x = 2
        self._invader_origin_y = 1
        self._invader_dir = 1
        self._invader_speed = 3
        self._invaders = {
            (row, col) for row in range(self._invader_rows) for col in range(self._invader_cols)
        }
        self._player_x = max(2, width // 2)
        self._bullet = None

    def _reset_pong(self) -> None:
        width, height = self._board_width, self._board_height
        self._pong_ball = [width // 2, height // 2]
        self._pong_dir = [1, 1]
        self._pong_paddle = max(2, height // 4)
        self._pong_left_y = max(1, height // 2 - self._pong_paddle // 2)
        self._pong_right_y = self._pong_left_y

    def _tick(self) -> None:
        if not self.active:
            return
        self._frame += 1
        self._advance_stars()
        if self.mode == "pong":
            self._tick_pong()
        else:
            self._tick_invaders()

    def _advance_stars(self) -> None:
        width, height = self._board_width, self._board_height
        updated = []
        for x, y in self._stars:
            y += 1
            if y < height:
                updated.append((x, y))
        if self._rng.random() < 0.35:
            updated.append((self._rng.randrange(1, max(2, width - 1)), 0))
        self._stars = updated

    def _invader_positions(self) -> dict:
        positions = {}
        for row, col in self._invaders:
            x = self._invader_origin_x + col * 3
            y = self._invader_origin_y + row * 2
            positions[(x, y)] = (row, col)
        return positions

    def _tick_invaders(self) -> None:
        width, height = self._board_width, self._board_height
        if not self._invaders:
            self._reset_invaders()
        if self._frame % self._invader_speed == 0:
            next_origin = self._invader_origin_x + self._invader_dir
            min_x = next_origin
            max_x = next_origin + (self._invader_cols - 1) * 3
            if min_x <= 1 or max_x >= width - 2:
                self._invader_dir *= -1
                self._invader_origin_y += 1
            else:
                self._invader_origin_x = next_origin
        if self._invader_origin_y + (self._invader_rows - 1) * 2 >= height - 3:
            self._reset_invaders()

        positions = self._invader_positions()
        target_x = None
        if positions:
            target_x = min(positions.keys(), key=lambda pos: abs(pos[0] - self._player_x))[0]
            if target_x > self._player_x:
                self._player_x += 1
            elif target_x < self._player_x:
                self._player_x -= 1

        player_y = max(1, height - 2)
        self._player_x = max(1, min(width - 2, self._player_x))

        if self._bullet:
            self._bullet[1] -= 1
            if self._bullet[1] <= 0:
                self._bullet = None
            else:
                hit_key = (self._bullet[0], self._bullet[1])
                hit = positions.pop(hit_key, None)
                if hit:
                    self._invaders.discard(hit)
                    self._bullet = None

        if (
            self._bullet is None
            and target_x is not None
            and self._frame % 6 == 0
            and abs(target_x - self._player_x) <= 1
        ):
            self._bullet = [self._player_x, player_y - 1]

        grid = self._blank_grid()
        for x, y in self._stars:
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "."
        for (x, y), _ in positions.items():
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "W"
        if self._bullet:
            x, y = self._bullet
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "|"
        if 0 <= player_y < height:
            grid[player_y][self._player_x] = "A"
        self._render_grid(grid)

    def _tick_pong(self) -> None:
        width, height = self._board_width, self._board_height
        ball_x, ball_y = self._pong_ball
        dir_x, dir_y = self._pong_dir

        target_left = ball_y - self._pong_paddle // 2
        if target_left > self._pong_left_y:
            self._pong_left_y += 1
        elif target_left < self._pong_left_y:
            self._pong_left_y -= 1

        target_right = ball_y - self._pong_paddle // 2
        if target_right > self._pong_right_y:
            self._pong_right_y += 1
        elif target_right < self._pong_right_y:
            self._pong_right_y -= 1
        max_paddle_y = max(0, height - self._pong_paddle - 1)
        self._pong_left_y = max(0, min(max_paddle_y, self._pong_left_y))
        self._pong_right_y = max(0, min(max_paddle_y, self._pong_right_y))

        ball_x += dir_x
        ball_y += dir_y

        if ball_y <= 0 or ball_y >= height - 1:
            dir_y *= -1
            ball_y = max(0, min(height - 1, ball_y))

        if ball_x <= 1:
            if self._pong_left_y <= ball_y <= self._pong_left_y + self._pong_paddle - 1:
                dir_x = 1
            else:
                self._reset_pong()
                ball_x, ball_y = self._pong_ball
                dir_x, dir_y = self._pong_dir
        elif ball_x >= width - 2:
            if self._pong_right_y <= ball_y <= self._pong_right_y + self._pong_paddle - 1:
                dir_x = -1
            else:
                self._reset_pong()
                ball_x, ball_y = self._pong_ball
                dir_x, dir_y = self._pong_dir

        self._pong_ball = [ball_x, ball_y]
        self._pong_dir = [dir_x, dir_y]

        grid = self._blank_grid()
        for x, y in self._stars:
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "."
        for offset in range(self._pong_paddle):
            left_y = self._pong_left_y + offset
            right_y = self._pong_right_y + offset
            if 0 <= left_y < height:
                grid[left_y][1] = "|"
            if 0 <= right_y < height:
                grid[right_y][width - 2] = "|"
        if 0 <= ball_x < width and 0 <= ball_y < height:
            grid[ball_y][ball_x] = "o"
        self._render_grid(grid)

    def _blank_grid(self) -> list:
        return [[" " for _ in range(self._board_width)] for _ in range(self._board_height)]

    def _render_grid(self, grid: list) -> None:
        lines = ["".join(row) for row in grid]
        self.update("\n".join(lines))

    def _render_idle(self) -> None:
        width, height = self._board_width, self._board_height
        label = "SYSTEM READY"
        sub = "SEND A COMMAND TO START"
        lines = []
        for row in range(height):
            if row == height // 2 - 1:
                lines.append(label.center(width))
            elif row == height // 2:
                lines.append(sub.center(width))
            else:
                lines.append(" " * width)
        self.update("\n".join(lines))

    def _render_off(self) -> None:
        width, height = self._board_width, self._board_height
        label = "ARCADE OFF"
        lines = []
        for row in range(height):
            if row == height // 2:
                lines.append(label.center(width))
            else:
                lines.append(" " * width)
        self.update("\n".join(lines))

    def _render_frame(self) -> None:
        if self.mode == "pong":
            self._tick_pong()
        else:
            self._tick_invaders()


# --- MODAL: EKRAN WERYFIKACJI ---
class ToolApprovalScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("left", "focus_previous", "Lewo", show=False),
        Binding("right", "focus_next", "Prawo", show=False),
    ]

    def __init__(self, tool_name: str, command: str, reason: str, backend, tool_payload=None):
        super().__init__()
        self.tool_name = tool_name
        self.command = command
        self.reason = reason
        self.backend = backend
        self.tool_payload = tool_payload or {}

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return f"{text[:limit]}... (truncated)"

    def _limit_lines(self, text: str, max_lines: int) -> str:
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return text
        trimmed = lines[:max_lines]
        trimmed.append(f"... ({len(lines) - max_lines} more lines)")
        return "\n".join(trimmed)

    def _build_preview(self) -> str:
        payload = self.tool_payload if isinstance(self.tool_payload, dict) else {}
        tool_name = (payload.get("tool_name") or self.tool_name or "").lower()

        if tool_name in ("write_file", "file_write"):
            path = payload.get("path") or payload.get("file") or payload.get("target") or ""
            content = payload.get("content")
            if content is None and "text" in payload:
                content = payload.get("text")
            if content is None:
                return ""
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            preview = self._limit_lines(content, 12)
            return f"write_file -> {path}\n{preview}".strip()

        if tool_name in ("replace_text", "replace"):
            path = payload.get("path") or payload.get("file") or payload.get("target") or ""
            old = payload.get("old") or payload.get("find")
            new = payload.get("new") or payload.get("replace")
            if old is None or new is None:
                return ""
            old_text = self._truncate_text(str(old), 200)
            new_text = self._truncate_text(str(new), 200)
            return (
                f"replace_text -> {path}\n" f"--- OLD ---\n{old_text}\n" f"--- NEW ---\n{new_text}"
            ).strip()

        if tool_name in ("apply_patch", "patch"):
            patch_text = payload.get("patch") or payload.get("diff")
            if not patch_text:
                return ""
            preview = self._limit_lines(str(patch_text), 16)
            return f"apply_patch\n{preview}".strip()

        if tool_name in ("read_file", "read"):
            path = payload.get("path") or payload.get("file") or payload.get("target") or ""
            start_line = payload.get("start_line")
            end_line = payload.get("end_line")
            return f"read_file -> {path}\nlines: {start_line}-{end_line}".strip()

        if tool_name in ("list_files", "tree", "ls"):
            path = payload.get("path") or payload.get("dir") or "."
            max_depth = payload.get("max_depth")
            max_files = payload.get("max_files")
            return f"list_files -> {path}\nmax_depth: {max_depth}, max_files: {max_files}".strip()

        if tool_name in ("search_text", "search", "rg"):
            query = payload.get("query") or payload.get("pattern") or payload.get("text") or ""
            path = payload.get("path") or "."
            return f"search_text -> {path}\nquery: {self._truncate_text(str(query), 200)}".strip()

        if tool_name in ("terminal", "shell", "command"):
            command = payload.get("command") or self.command
            if not command:
                return ""
            return f"shell\n{command}".strip()

        if payload:
            try:
                payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
            except TypeError:
                payload_text = str(payload)
            return self._limit_lines(payload_text, 12)

        return ""

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("⚠️ AGENT ZERO: INTERWENCJA BEZPIECZEŃSTWA", id="risk-header")
            yield Label(f"\n[bold]Narzędzie:[/] {self.tool_name}", markup=True)
            yield Label(f"[bold]Powód:[/] {self.reason}", markup=True)
            yield Static(f"$ {self.command}", id="command-box")
            preview = self._build_preview()
            if preview:
                with VerticalScroll(id="preview-container"):
                    yield Static(preview, id="preview-box")
            yield Static("", id="explanation-area", classes="explanation-text")
            with Horizontal(id="buttons-layout"):
                yield Button("Zatwierdź (Y)", classes="success", id="approve")
                yield Button("Wyjaśnij (E)", classes="warning", id="explain")
                yield Button("Odrzuć (N)", classes="error", id="reject")

    def on_mount(self) -> None:
        self.query_one("#explain").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "approve":
            self.dismiss("approved")
        elif btn_id == "reject":
            self.dismiss("rejected")
        elif btn_id == "explain":
            explanation_widget = self.query_one("#explanation-area", Static)
            explanation_widget.update("[blink]Pytam model AI o analizę ryzyka...[/]")
            explanation = await self.backend.explain_risk(self.command)
            explanation_widget.update(explanation)
            event.button.disabled = True
            event.button.label = "Analiza Gotowa"
            self.query_one("#reject").focus()


# --- RETRO GAME SCREEN: AGENT ZUSA (THE ONES) ---
class RetroGameScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Powrót")]

    CITIES = [
        "Warszawa",
        "Kraków",
        "Łódź",
        "Wrocław",
        "Poznań",
        "Gdańsk",
        "Szczecin",
        "Bydgoszcz",
        "Lublin",
        "Białystok",
        "Katowice",
        "Gdynia",
        "Częstochowa",
        "Radom",
        "Toruń",
        "Sosnowiec",
        "Rzeszów",
        "Kielce",
        "Gliwice",
        "Zabrze",
        "Olsztyn",
        "Bielsko-Biała",
        "Bytom",
        "Zielona Góra",
        "Rybnik",
        "Pszczew",
        "Maków Podh.",
    ]

    def compose(self) -> ComposeResult:
        yield Label("MISSION: POLAND | AGENT: THE ONES (Zero)", id="game-header")
        with Container(id="game-board"):
            for i, city in enumerate(self.CITIES):
                yield Button(f"{city}", classes="city-node", id=f"city-{i}")
        yield Footer()

    def on_mount(self) -> None:
        self.tokens = 50  # Startowe Tokeny
        self.cities_lost = 0
        self.agent_pos = 0  # Start w Warszawie

        # FIX: Konwersja DOMQuery na listę, aby działało .index()
        self.buttons = list(self.query(".city-node"))

        # Oznacz start
        self.update_agent_visuals()

        # EvilAGI atakuje co 1.5 sekundy
        self.spawn_timer = self.set_interval(1.5, self.spawn_evil_agi)

        # Sprawdzanie zniszczeń
        self.explode_timer = self.set_interval(0.5, self.check_system_failure)

        self.update_header()

    def update_agent_visuals(self):
        # Reset visuali agenta
        for btn in self.buttons:
            if "agent-here" in btn.classes:
                btn.remove_class("agent-here")
                # Przywróć nazwę miasta bez ikonki
                city_name = self.CITIES[self.buttons.index(btn)]
                if "evil-agi" in btn.classes:
                    btn.label = f"☠ {city_name}"
                elif "secure" in btn.classes:
                    btn.label = f"🛡 {city_name}"
                else:
                    btn.label = city_name

        # Ustaw nowego agenta
        current_btn = self.buttons[self.agent_pos]
        current_btn.add_class("agent-here")
        # Łysy z brodą - ASCII art icon
        current_btn.label = f"[🧔] {self.CITIES[self.agent_pos]}"

    def spawn_evil_agi(self):
        target = random.choice(self.buttons)
        # Nie atakuj tam gdzie stoi agent, ani tam gdzie już jest zniszczone/zainfekowane
        if (
            target != self.buttons[self.agent_pos]
            and "evil-agi" not in target.classes
            and "destroyed" not in target.classes
        ):
            target.add_class("evil-agi")
            target.remove_class("secure")
            city_name = self.CITIES[self.buttons.index(target)]
            target.label = f"☠ {city_name}"
            target.infection_start = datetime.now().timestamp()

    def check_system_failure(self):
        now = datetime.now().timestamp()
        for node in self.buttons:
            if "evil-agi" in node.classes and hasattr(node, "infection_start"):
                # Jeśli infekcja trwa dłużej niż 5 sekund -> System Lost
                if now - node.infection_start > 5.0:
                    node.remove_class("evil-agi")
                    node.add_class("destroyed")
                    node.label = "--- LOST ---"
                    self.cities_lost += 1
                    self.update_header()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        target_btn = event.button
        target_index = int(target_btn.id.split("-")[1])

        # Jeśli miasto zniszczone - brak ruchu
        if "destroyed" in target_btn.classes:
            return

        # LOGIKA GRY:

        # 1. Jeśli klikasz tam gdzie jesteś -> STAKING (Mnożenie Tokenów)
        if target_index == self.agent_pos:
            if "secure" in target_btn.classes:
                growth = max(1, int(self.tokens * 0.1))  # 10% zysku
                self.tokens += growth
                self.notify(f"STAKING: +{growth} Tokens")
            else:
                self.notify("Zabezpiecz teren przed stakingiem!")

        # 2. Jeśli klikasz inne miasto -> TELEPORTACJA
        else:
            self.agent_pos = target_index
            self.update_agent_visuals()

            # Jeśli wpadłeś na EvilAGI -> WALKA (Koszt Tokenów)
            if "evil-agi" in target_btn.classes:
                if self.tokens >= 10:
                    self.tokens -= 10
                    target_btn.remove_class("evil-agi")
                    target_btn.add_class("secure")
                    self.notify("EvilAGI zneutralizowane! (-10 Tokens)")
                else:
                    self.notify("Brak Tokenów na walkę! Uciekaj i mnóż!")

            # Jeśli wpadłeś na czyste/zabezpieczone -> Nic (lub mały bonus)
            elif "secure" not in target_btn.classes:
                target_btn.add_class("secure")  # Automatyczne zabezpieczenie przy odwiedzinach

        self.update_header()

    def update_header(self):
        status_color = "green" if self.tokens > 20 else "red"
        header = (
            f"TOKENS: [{status_color}]{self.tokens}[/] | "
            f"LOST NODES: {self.cities_lost}/5 | [ESC] Powrót"
        )
        self.query_one("#game-header").update(header)


# --- GŁÓWNA APLIKACJA ---
class AgentZeroCLI(App):
    CSS = CSS
    TITLE = "Agent Zero CLI"
    SUB_TITLE = "Initializing..."
    READONLY_TOOLS = {
        "read_file",
        "read",
        "list_files",
        "tree",
        "ls",
        "search_text",
        "search",
        "rg",
    }

    BINDINGS = [
        ("ctrl+p", "command_palette", "Palette"),
        ("f1", "push_game", "Graj w Agent ZUSA"),
        ("ctrl+c", "quit", "Wyjście"),
    ]

    def __init__(self):
        super().__init__()
        self.base_config = CONFIG or {}
        self.projects = self.base_config.get("projects") or {}
        if not self.projects:
            workspace_root = self.base_config.get("connection", {}).get("workspace_root") or "."
            self.projects = {"default": {"workspace_root": workspace_root}}
        self.agent_profiles = self.base_config.get("agent_profiles") or {"default": {}}
        self.current_project = self.base_config.get("active_project") or next(
            iter(self.projects.keys())
        )
        self.current_profile = self.base_config.get("agent_profile") or next(
            iter(self.agent_profiles.keys())
        )
        project_profile = self.projects.get(self.current_project, {}).get("agent_profile")
        if project_profile:
            self.current_profile = project_profile
        if self.current_profile not in self.agent_profiles:
            self.current_profile = next(iter(self.agent_profiles.keys()))
        self.last_status = "Idle"
        self.last_tool = "None"
        self.last_context_status = ""
        self.waiting = False
        self._theme_class = None
        self.active_config = self._build_active_config()
        self.ui_config = self.active_config.get("ui", {})
        self.theme_name = self._resolve_theme_name(self.ui_config.get("theme"))
        self.arcade_mode = self._resolve_arcade_mode(self.ui_config.get("waiting_game"))
        self._register_themes()
        self.theme = self.theme_name
        self._init_backend()
        self._update_subtitle()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="app-body"):
            with Horizontal(id="brand-bar"):
                yield Static("AGENT ZERO // REMOTE OPERATOR", id="brand-title")
                yield Static("", id="brand-meta")
                yield Static("", id="brand-signal")
            with Horizontal(id="main-row"):
                yield VerticalScroll(id="chat-container")
                with VerticalScroll(id="side-panel"):
                    yield Static("", id="session-card", classes="panel")
                    yield Static("", id="connection-card", classes="panel")
                    yield Static("", id="context-card", classes="panel")
                    yield Static("", id="live-card", classes="panel")
                    with Container(id="activity-card", classes="panel"):
                        yield Static("LIVE FEED", classes="panel-title", id="activity-title")
                        yield RichLog(id="activity-feed", wrap=True, markup=False)
                    with Container(id="arcade-card", classes="panel"):
                        yield Static("ARCADE", classes="panel-title", id="arcade-title")
                        yield ArcadeWidget(self.arcade_mode, id="arcade-screen")
        yield Input(placeholder="Wpisz polecenie...", id="input-area")
        yield Footer()

    def on_mount(self) -> None:
        self._apply_ui_config()
        chat = self.query_one("#chat-container")
        security_mode = self.active_config.get("security", {}).get("mode", "balanced")
        welcome_msg = (
            "Connected · "
            f"{self.current_project} · "
            f"{self.current_profile} · "
            f"{security_mode} · "
            f"{self.theme_name}"
        )
        chat.mount(Static(welcome_msg, classes="status-msg"))
        self._refresh_side_panel()
        self._update_brand_bar()

    def action_push_game(self) -> None:
        self.push_screen(RetroGameScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        if not user_input:
            return
        event.input.value = ""
        chat = self.query_one("#chat-container")
        await chat.mount(Markdown(f"**TY:** {user_input}", classes="user-msg"))
        chat.scroll_end()
        self.run_worker(self.process_agent_interaction(user_input))

    async def process_agent_interaction(self, user_text: str):
        self._append_feed("user", user_text)
        self._set_waiting(True)
        try:
            await self._handle_events(self.backend.send_prompt(user_text))
        finally:
            self._set_waiting(False)

    async def _handle_events(self, event_stream):
        chat = self.query_one("#chat-container")
        async for event in event_stream:
            event_type = event.get("type")
            if event_type == "status":
                content = event.get("content", "")
                self._append_feed("status", content)
                if self.ui_config.get("status_in_chat", False):
                    await chat.mount(Static(content, classes="status-msg"))
                self.last_status = content or self.last_status
                if content.startswith("Context ready"):
                    self.last_context_status = content
                self._refresh_side_panel()
            elif event_type in ("thought", "thinking"):
                self._append_feed("thinking", event.get("content", ""))
            elif event_type == "final_response":
                self._append_feed("agent", event.get("content", ""))
                await chat.mount(
                    AnimatedMarkdown(
                        f"**AGENT:** {event.get('content', '')}",
                        classes="agent-msg",
                        speed=0.012,
                        chunk_size=10,
                        max_chars=4000,
                    )
                )
                self._set_waiting(False)
            elif event_type == "tool_output":
                self._append_feed("tool", event.get("content", ""))
                await chat.mount(
                    AnimatedText(
                        event.get("content", ""),
                        classes="tool-output",
                        speed=0.004,
                        chunk_size=12,
                        max_chars=4000,
                    )
                )
            elif event_type == "tool_request":
                tool_payload = event.get("payload") or event
                tool_name = event.get("tool_name", "tool")
                command = event.get("command", "")
                self._append_feed("tool", f"{tool_name} {command}".strip())
                self.last_tool = f"{tool_name}: {command}" if command else tool_name
                self._refresh_side_panel()
                auto_approved = self._should_auto_approve(event)
                if auto_approved:
                    decision = "approved"
                    self._append_feed("approval", f"auto-approved {command}".strip())
                    await chat.mount(
                        Static(
                            f"✅ AUTO-ZATWIERDZONO: {event.get('command', '')}",
                            classes="status-msg",
                        )
                    )
                else:
                    decision = await self.push_screen_wait(
                        ToolApprovalScreen(
                            event.get("tool_name", "tool"),
                            event.get("command", ""),
                            event.get("reason", ""),
                            self.backend,
                            tool_payload=tool_payload,
                        )
                    )
                if decision == "approved":
                    if not auto_approved:
                        await chat.mount(
                            Static(
                                f"✅ ZATWIERDZONO: {event.get('command', '')}",
                                classes="status-msg",
                            )
                        )
                        self._append_feed("approval", f"approved {command}".strip())
                    await self._handle_events(self.backend.execute_tool(event))
                else:
                    self._append_feed("approval", f"rejected {command}".strip())
                    await chat.mount(Static("❌ ODRZUCONO.", classes="status-msg"))
                    if hasattr(self.backend, "reject_tool"):
                        await self._handle_events(self.backend.reject_tool(event))
            else:
                self._append_feed("event", str(event))
                if self.ui_config.get("status_in_chat", False):
                    await chat.mount(Static(str(event), classes="status-msg"))
            chat.scroll_end()

    def _is_shell_whitelisted(self, command: str) -> bool:
        whitelist = self.active_config.get("security", {}).get("whitelist") or []
        cmd = (command or "").strip().lower()
        for entry in whitelist:
            entry_text = str(entry).strip().lower()
            if entry_text and cmd.startswith(entry_text):
                return True
        return False

    def _should_auto_approve(self, event: dict) -> bool:
        mode = self.active_config.get("security", {}).get("mode", "balanced")
        tool_name = (event.get("tool_name") or "").lower()
        if mode == "god_mode":
            return True
        if mode == "balanced":
            if tool_name in self.READONLY_TOOLS:
                return True
            if tool_name in ("terminal", "shell", "command"):
                return self._is_shell_whitelisted(event.get("command", ""))
            return False
        return False

    def get_system_commands(self, screen):
        yield from super().get_system_commands(screen)
        for name in sorted(self.projects.keys()):
            if name == self.current_project:
                continue
            yield SystemCommand(
                f"Project: {name}",
                f"Switch to project '{name}'",
                lambda n=name: self.action_switch_project(n),
            )
        for name in sorted(self.agent_profiles.keys()):
            if name == self.current_profile:
                continue
            yield SystemCommand(
                f"Agent: {name}",
                f"Switch agent profile to '{name}'",
                lambda n=name: self.action_switch_agent_profile(n),
            )
        for name in THEME_PRESETS.keys():
            if name == self.theme_name:
                continue
            yield SystemCommand(
                f"Theme: {name}",
                f"Switch theme to '{name}'",
                lambda n=name: self.action_switch_theme(n),
            )

    def action_switch_project(self, project_name: str) -> None:
        if project_name not in self.projects:
            self.run_worker(self._append_system_message(f"❌ Unknown project: {project_name}"))
            return
        self.current_project = project_name
        project_profile = self.projects.get(project_name, {}).get("agent_profile")
        if project_profile:
            self.current_profile = project_profile
        if self.current_profile not in self.agent_profiles:
            self.current_profile = next(iter(self.agent_profiles.keys()))
        self.last_context_status = ""
        self.active_config = self._build_active_config()
        self._init_backend()
        self._apply_ui_config()
        self.run_worker(
            self._append_system_message(
                f"✅ Switched project to '{project_name}' " f"(profile: {self.current_profile})."
            )
        )

    def action_switch_agent_profile(self, profile_name: str) -> None:
        if profile_name not in self.agent_profiles:
            self.run_worker(
                self._append_system_message(f"❌ Unknown agent profile: {profile_name}")
            )
            return
        self.current_profile = profile_name
        self.last_context_status = ""
        self.active_config = self._build_active_config()
        self._init_backend()
        self._apply_ui_config()
        self.run_worker(
            self._append_system_message(f"✅ Switched agent profile to '{profile_name}'.")
        )

    def action_switch_theme(self, theme_name: str) -> None:
        resolved = self._resolve_theme_name(theme_name)
        if resolved not in THEME_PRESETS:
            self.run_worker(self._append_system_message(f"❌ Unknown theme: {theme_name}"))
            return
        self._apply_theme(resolved)
        self.active_config.setdefault("ui", {})["theme"] = resolved
        self.run_worker(self._append_system_message(f"✅ Switched theme to '{resolved}'."))

    def _register_themes(self) -> None:
        for theme in THEME_PRESETS.values():
            self.register_theme(theme)

    def _resolve_theme_name(self, theme_name) -> str:
        if not theme_name:
            return DEFAULT_THEME
        raw = str(theme_name).strip()
        if raw in THEME_PRESETS:
            return raw
        alias = THEME_ALIASES.get(raw.lower())
        if alias:
            return alias
        slug = _slugify_theme(raw)
        for candidate in THEME_PRESETS.keys():
            if _slugify_theme(candidate) == slug:
                return candidate
        return DEFAULT_THEME

    def _resolve_arcade_mode(self, mode) -> str:
        if not mode:
            return "invaders"
        value = str(mode).strip().lower()
        if value in ("off", "none", "disabled", "false"):
            return "off"
        if value in ("pong",):
            return "pong"
        if value in ("invaders", "space", "space-invaders", "tetris"):
            return "invaders"
        return "invaders"

    def _apply_theme(self, theme_name: str) -> None:
        resolved = self._resolve_theme_name(theme_name)
        self.theme_name = resolved
        self.theme = resolved
        self._apply_theme_class(resolved)
        self._update_subtitle()
        self._refresh_side_panel()
        self._update_brand_bar()

    def _apply_ui_config(self) -> None:
        self.ui_config = self.active_config.get("ui", {})
        self.theme_name = self._resolve_theme_name(self.ui_config.get("theme"))
        self.arcade_mode = self._resolve_arcade_mode(self.ui_config.get("waiting_game"))
        self._apply_theme(self.theme_name)
        try:
            arcade = self.query_one("#arcade-screen", ArcadeWidget)
            arcade.set_mode(self.arcade_mode)
            if not self.waiting:
                arcade.stop()
            title = self.query_one("#arcade-title", Static)
            state = "WAITING" if self.waiting else "IDLE"
            title.update(f"ARCADE / {arcade.mode.upper()} / {state}")
        except Exception:
            pass

    def _apply_theme_class(self, theme_name: str) -> None:
        if self._theme_class:
            self.set_class(False, self._theme_class)
        theme_class = f"theme-{_slugify_theme(theme_name)}"
        self.set_class(True, theme_class)
        self._theme_class = theme_class

    def _set_waiting(self, active: bool) -> None:
        if self.waiting == active:
            return
        self.waiting = active
        if active:
            self._append_feed("system", "waiting for agent response")
        else:
            self._append_feed("system", "response received")
        try:
            arcade = self.query_one("#arcade-screen", ArcadeWidget)
            if active:
                arcade.start()
            else:
                arcade.stop()
            title = self.query_one("#arcade-title", Static)
            state = "WAITING" if active else "IDLE"
            title.update(f"ARCADE / {arcade.mode.upper()} / {state}")
        except Exception:
            pass
        self._refresh_side_panel()
        self._update_brand_bar()

    def _update_brand_bar(self) -> None:
        try:
            title = self.query_one("#brand-title", Static)
            meta = self.query_one("#brand-meta", Static)
            signal = self.query_one("#brand-signal", Static)
        except Exception:
            return
        mode = self.active_config.get("security", {}).get("mode", "balanced").upper()
        status = "BUSY" if self.waiting else "READY"
        title.update("Agent Zero")
        meta.update(f"{self.current_project} · {self.current_profile} · {mode} · {self.theme_name}")
        signal.update(status)

    def _truncate_feed(self, text: str, limit: int = 160) -> str:
        if not text:
            return ""
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: max(0, limit - 3)]}..."

    def _format_feed_line(self, label: str, content: str) -> str:
        if not content:
            return ""
        show_ts = bool(self.ui_config.get("show_timestamps", False))
        timestamp = ""
        if show_ts:
            timestamp = datetime.now().strftime("%H:%M:%S") + "  "
        tag = (label or "event").lower().ljust(9)
        body = self._truncate_feed(content)
        return f"{timestamp}{tag}{body}"

    def _append_feed(self, label: str, content: str) -> None:
        line = self._format_feed_line(label, content)
        if not line:
            return
        try:
            feed = self.query_one("#activity-feed", RichLog)
            feed.write(line, scroll_end=True)
        except Exception:
            pass

    def _init_backend(self) -> None:
        connection = self.active_config.get("connection", {})
        if connection.get("use_mock", False):
            self.backend = MockAgentBackend()
        else:
            self.backend = RemoteAgentBackend(self.active_config)

    def _normalize_project_override(self, project_cfg: dict) -> dict:
        override = copy.deepcopy(project_cfg) if isinstance(project_cfg, dict) else {}
        connection_override = override.get("connection", {})
        for key in (
            "workspace_root",
            "api_url",
            "api_key",
            "timeout_seconds",
            "lifetime_hours",
            "stream",
            "stream_mode",
            "keepalive_seconds",
            "max_wait_seconds",
        ):
            if key in override:
                connection_override[key] = override.pop(key)
        if connection_override:
            override["connection"] = connection_override
        if "security_mode" in override:
            security_override = override.get("security", {})
            security_override["mode"] = override.pop("security_mode")
            override["security"] = security_override
        return override

    def _deep_merge(self, base: dict, override: dict) -> dict:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)
        return base

    def _build_active_config(self) -> dict:
        config = copy.deepcopy(self.base_config)
        project_cfg = self.projects.get(self.current_project, {})
        project_override = self._normalize_project_override(project_cfg)
        config = self._deep_merge(config, project_override)
        if self.current_profile:
            config["agent_profile"] = self.current_profile
        config["active_project"] = self.current_project
        return config

    def _update_subtitle(self) -> None:
        mode = self.active_config.get("security", {}).get("mode", "balanced").upper()
        self.sub_title = (
            f"Mode: {mode} | Project: {self.current_project} | "
            f"Agent: {self.current_profile} | Theme: {self.theme_name} | "
            "F1: MISSION POLAND"
        )

    def _refresh_side_panel(self) -> None:
        try:
            session = self.query_one("#session-card", Static)
            connection = self.query_one("#connection-card", Static)
            context = self.query_one("#context-card", Static)
            live = self.query_one("#live-card", Static)
        except Exception:
            return
        session.update(self._render_session_card())
        connection.update(self._render_connection_card())
        context.update(self._render_context_card())
        live.update(self._render_live_card())
        self._update_brand_bar()

    def _render_session_card(self) -> str:
        mode = self.active_config.get("security", {}).get("mode", "balanced").upper()
        workspace = self.active_config.get("connection", {}).get("workspace_root", ".")
        return (
            "[b]SESSION[/b]\n"
            f"Project: {self.current_project}\n"
            f"Agent: {self.current_profile}\n"
            f"Mode: {mode}\n"
            f"Theme: {self.theme_name}\n"
            f"Workspace: {workspace}"
        )

    def _render_connection_card(self) -> str:
        connection = self.active_config.get("connection", {})
        api_url = (
            connection.get("api_url")
            or f"http://{connection.get('host')}:{connection.get('port')}{connection.get('path')}"
        )
        stream = "on" if connection.get("stream", False) else "off"
        timeout = connection.get("timeout_seconds", 0)
        keepalive = connection.get("keepalive_seconds", 0)
        return (
            "[b]CONNECTION[/b]\n"
            f"API: {api_url}\n"
            f"Stream: {stream}\n"
            f"Timeout: {timeout}s\n"
            f"Keepalive: {keepalive}s"
        )

    def _render_context_card(self) -> str:
        context_cfg = self.active_config.get("context", {})
        mode = context_cfg.get("mode", "manual")
        tree = "on" if context_cfg.get("include_tree", False) else "off"
        previews = "on" if context_cfg.get("include_previews", False) else "off"
        max_bytes = context_cfg.get("max_bytes", 0)
        status_line = self.last_context_status or "Context pending."
        return (
            "[b]CONTEXT[/b]\n"
            f"Mode: {mode}\n"
            f"Tree: {tree}, Previews: {previews}\n"
            f"Max bytes: {max_bytes}\n"
            f"{status_line}"
        )

    def _render_live_card(self) -> str:
        waiting = "YES" if self.waiting else "NO"
        return (
            "[b]LIVE[/b]\n"
            f"Status: {self.last_status}\n"
            f"Last tool: {self.last_tool}\n"
            f"Waiting: {waiting}"
        )

    async def _append_system_message(self, text: str) -> None:
        chat = self.query_one("#chat-container")
        await chat.mount(Static(text, classes="system-msg"))
        chat.scroll_end()


if __name__ == "__main__":
    setup_logging()
    app = AgentZeroCLI()
    app.run()
