"""Main AgentZeroCLI application class."""

import asyncio
import copy
import os
import shutil
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Markdown, RichLog, Static

from .chat.message_widgets import AnimatedMarkdown, AnimatedText
from .chat.multiline_input import MultilineInput
from .chat.session import SessionManager
from .chat.thinking_stream import ThinkingStreamWidget
from .commands.slash_commands import SlashCommandRegistry
from .css import CSS
from .screens.file_upload import FileUploadScreen
from .screens.observer_config import ObserverConfigScreen
from .screens.space_invaders import SpaceInvadersScreen
from .screens.tool_approval import ToolApprovalScreen
from .themes import THEME_PRESETS, resolve_theme_name
from .widgets.arcade import ArcadeWidget
from .widgets.hierarchical_menu import HierarchicalMenu
from .widgets.thinking_indicator import BrandBarIndicator, ThinkingIndicator
from .insights import get_mixed_feed_item, format_feed_item

from ..backend import get_backend


def _slugify_theme(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


class AgentZeroCLI(App):
    """Main TUI application for Agent Zero remote control."""

    TITLE = "Agent Zero"
    SUB_TITLE = "Remote Operator Panel"
    CSS = CSS

    BINDINGS = [
        Binding("f1", "show_help", "Help"),
        Binding("f2", "toggle_menu", "Menu"),
        Binding("f3", "push_game", "Game"),
        Binding("f5", "open_agent_ui", "Agent Zero UI"),
        Binding("f10", "quit", "Quit"),
        Binding("escape", "close_menu", "Close", show=False),
    ]

    READONLY_TOOLS = frozenset(
        {"read_file", "read", "list_files", "tree", "ls", "search_text", "search", "rg"}
    )

    def __init__(self):
        super().__init__()
        self.base_config = self._load_config()
        self.projects = self.base_config.get("projects", {"default": {}})
        self.agent_profiles = self.base_config.get("agent_profiles", {"default": {}})
        self.current_project = next(iter(self.projects.keys()))
        self.current_profile = next(iter(self.agent_profiles.keys()))
        self.active_config = self._build_active_config()
        self.ui_config = self.active_config.get("ui", {})
        self.theme_name = resolve_theme_name(self.ui_config.get("theme"))
        self.arcade_mode = self._resolve_arcade_mode(self.ui_config.get("waiting_game"))
        self._theme_class = ""
        self.waiting = False
        self.last_status = ""
        self.last_tool = ""
        self.last_context_status = ""
        self.backend = None
        self.session_manager = SessionManager()
        self.slash_commands = SlashCommandRegistry()
        self._menu_visible = False
        self._register_themes()
        self.theme = self.theme_name
        self._init_backend()

    def _load_config(self) -> dict:
        config_paths = [
            Path("config.yaml"),
            Path.home() / ".config" / "agentzero" / "config.yaml",
        ]
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
        return {"security": {"mode": "balanced"}}

    def _build_active_config(self) -> dict:
        config = copy.deepcopy(self.base_config)
        project_cfg = self.projects.get(self.current_project, {})
        config = self._deep_merge(config, self._normalize_project_override(project_cfg))
        if self.current_profile:
            config["agent_profile"] = self.current_profile
        config["active_project"] = self.current_project
        return config

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

    def _init_backend(self) -> None:
        self.backend = get_backend()

    def _register_themes(self) -> None:
        for theme in THEME_PRESETS.values():
            self.register_theme(theme)

    def _resolve_arcade_mode(self, mode) -> str:
        if not mode:
            return "invaders"
        value = str(mode).strip().lower()
        if value in ("off", "none", "disabled", "false"):
            return "off"
        if value == "pong":
            return "pong"
        return "invaders"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield HierarchicalMenu(
            projects=self.projects,
            agents=self.agent_profiles,
            themes=list(THEME_PRESETS.keys()),
            current_project=self.current_project,
            current_agent=self.current_profile,
            current_theme=self.theme_name,
            id="menu-container",
            classes="hidden",
        )
        with Vertical(id="app-body"):
            with Horizontal(id="brand-bar"):
                yield Static("Agent Zero", id="brand-title")
                yield Static("", id="brand-meta")
                yield BrandBarIndicator(id="brand-signal")
            with Horizontal(id="main-row"):
                with Vertical(id="chat-area"):
                    yield VerticalScroll(id="chat-container")
                    yield ThinkingIndicator(id="thinking-indicator", classes="thinking-indicator")
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
        yield MultilineInput(placeholder="Type command or /help...", id="input-area")
        yield Footer()

    def on_mount(self) -> None:
        self._apply_ui_config()
        chat = self.query_one("#chat-container")
        security_mode = self.active_config.get("security", {}).get("mode", "balanced")
        welcome = (
            f"Connected | {self.current_project} | {self.current_profile} | "
            f"{security_mode} | {self.theme_name}"
        )
        chat.mount(Static(welcome, classes="status-msg"))
        chat.mount(
            Static(
                "Type /help for commands | F1=Help F2=Menu F3=Game F10=Quit",
                classes="status-msg",
            )
        )
        # Start periodic feed updates (news + project insights)
        self._feed_timer = self.set_interval(15, self._show_feed_item)
        # Show initial feed item
        self.call_later(self._show_feed_item)
    
    def _show_feed_item(self) -> None:
        """Show a mixed feed item (news or project insight) in activity panel."""
        if self.waiting:
            # More frequent updates during thinking
            workspace = self.active_config.get("connection", {}).get("workspace_root")
            item = get_mixed_feed_item(workspace)
            formatted = format_feed_item(item)
            self._append_feed("feed", formatted)

    async def on_multiline_input_submitted(self, event: MultilineInput.Submitted) -> None:
        text = event.value
        if not text:
            return
        if await self.slash_commands.execute(self, text):
            return
        chat = self.query_one("#chat-container")
        await chat.mount(Markdown(f"**YOU:** {text}", classes="user-msg"))
        chat.scroll_end()
        self.run_worker(self.process_agent_interaction(text))

    async def process_agent_interaction(self, user_text: str) -> None:
        self._append_feed("user", user_text)
        self._set_waiting(True)
        try:
            await self._handle_events(self.backend.send_prompt(user_text))
        finally:
            self._set_waiting(False)

    async def _handle_events(self, event_stream) -> None:
        chat = self.query_one("#chat-container")
        thinking_widget = None

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
                content = event.get("content", "")
                self._append_feed("thinking", content)
                if thinking_widget is None:
                    thinking_widget = ThinkingStreamWidget()
                    await chat.mount(thinking_widget)
                thinking_widget.add_thought(content)
                chat.scroll_end()

            elif event_type == "final_response":
                if thinking_widget:
                    thinking_widget.remove()
                    thinking_widget = None
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
                    await chat.mount(Static(f"AUTO-APPROVED: {command}", classes="status-msg"))
                else:
                    decision = await self.push_screen_wait(
                        ToolApprovalScreen(
                            tool_name, command, event.get("reason", ""), self.backend, tool_payload
                        )
                    )

                if decision == "approved":
                    if not auto_approved:
                        await chat.mount(Static(f"APPROVED: {command}", classes="status-msg"))
                        self._append_feed("approval", f"approved {command}".strip())
                    await self._handle_events(self.backend.execute_tool(event))
                else:
                    self._append_feed("approval", f"rejected {command}".strip())
                    await chat.mount(Static("REJECTED", classes="status-msg"))
                    if hasattr(self.backend, "reject_tool"):
                        await self._handle_events(self.backend.reject_tool(event))
            else:
                self._append_feed("event", str(event))

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

    def _set_waiting(self, active: bool) -> None:
        if self.waiting == active:
            return
        self.waiting = active
        self._append_feed("system", "waiting..." if active else "response received")
        try:
            thinking = self.query_one("#thinking-indicator", ThinkingIndicator)
            if active:
                thinking.start()
            else:
                thinking.stop()
            brand = self.query_one("#brand-signal", BrandBarIndicator)
            brand.set_thinking(active)
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

    def _append_feed(self, label: str, content: str) -> None:
        if not content:
            return
        try:
            feed = self.query_one("#activity-feed", RichLog)
            ts = datetime.now().strftime("%H:%M:%S")
            tag = label.lower().ljust(9)
            text = " ".join(str(content).split())[:160]
            show_ts = bool(self.ui_config.get("show_timestamps", False))
            prefix = f"{ts} " if show_ts else ""
            feed.write(f"{prefix}{tag} {text}", scroll_end=True)
        except Exception:
            pass

    def _update_brand_bar(self) -> None:
        try:
            meta = self.query_one("#brand-meta", Static)
            mode = self.active_config.get("security", {}).get("mode", "balanced").upper()
            meta.update(
                f"{self.current_project} | {self.current_profile} | {mode} | {self.theme_name}"
            )
        except Exception:
            pass

    def _refresh_side_panel(self) -> None:
        try:
            self.query_one("#session-card", Static).update(self._render_session_card())
            self.query_one("#connection-card", Static).update(self._render_connection_card())
            self.query_one("#context-card", Static).update(self._render_context_card())
            self.query_one("#live-card", Static).update(self._render_live_card())
        except Exception:
            pass

    def _render_session_card(self) -> str:
        mode = self.active_config.get("security", {}).get("mode", "balanced").upper()
        ws = self.active_config.get("connection", {}).get("workspace_root", ".")
        return (
            "[b]SESSION[/b]\n"
            f"Project: {self.current_project}\n"
            f"Agent: {self.current_profile}\n"
            f"Mode: {mode}\n"
            f"Theme: {self.theme_name}\n"
            f"Workspace: {ws}"
        )

    def _render_connection_card(self) -> str:
        conn = self.active_config.get("connection", {})
        url = conn.get("api_url", "not configured")
        stream = "on" if conn.get("stream", False) else "off"
        return f"[b]CONNECTION[/b]\nAPI: {url}\nStream: {stream}"

    def _render_context_card(self) -> str:
        ctx = self.active_config.get("context", {})
        mode = ctx.get("mode", "manual")
        return f"[b]CONTEXT[/b]\nMode: {mode}\n{self.last_context_status or 'Pending'}"

    def _render_live_card(self) -> str:
        waiting = "YES" if self.waiting else "NO"
        return (
            "[b]LIVE[/b]\n"
            f"Status: {self.last_status}\n"
            f"Last tool: {self.last_tool}\n"
            f"Waiting: {waiting}"
        )

    def _apply_ui_config(self) -> None:
        self.ui_config = self.active_config.get("ui", {})
        self.theme_name = resolve_theme_name(self.ui_config.get("theme"))
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

    def _apply_theme(self, theme_name: str) -> None:
        resolved = resolve_theme_name(theme_name)
        self.theme_name = resolved
        self.theme = resolved
        if self._theme_class:
            self.set_class(False, self._theme_class)
        theme_class = f"theme-{_slugify_theme(resolved)}"
        self.set_class(True, theme_class)
        self._theme_class = theme_class
        self._update_brand_bar()
        self._refresh_side_panel()

    # Actions
    def action_switch_project(self, project_name: str) -> None:
        if project_name not in self.projects:
            self.notify(f"Unknown project: {project_name}", severity="warning")
            return
        self.current_project = project_name
        project_profile = self.projects.get(project_name, {}).get("agent_profile")
        if project_profile and project_profile in self.agent_profiles:
            self.current_profile = project_profile
        self.active_config = self._build_active_config()
        self._init_backend()
        self._apply_ui_config()
        self.notify(f"Switched to project: {project_name}")
        self._update_brand_bar()
        self._refresh_side_panel()

    def action_switch_agent_profile(self, profile_name: str) -> None:
        if profile_name not in self.agent_profiles:
            self.notify(f"Unknown profile: {profile_name}", severity="warning")
            return
        self.current_profile = profile_name
        self.active_config = self._build_active_config()
        self._init_backend()
        self._apply_ui_config()
        self.notify(f"Switched to agent: {profile_name}")
        self._update_brand_bar()
        self._refresh_side_panel()

    def action_switch_theme(self, theme_name: str) -> None:
        resolved = resolve_theme_name(theme_name)
        if resolved not in THEME_PRESETS:
            self.notify(f"Unknown theme: {theme_name}", severity="warning")
            return
        self._apply_theme(resolved)
        self.notify(f"Switched to theme: {resolved}")

    def action_toggle_menu(self) -> None:
        menu = self.query_one("#menu-container", HierarchicalMenu)
        menu.toggle()
        self._menu_visible = not self._menu_visible

    def action_close_menu(self) -> None:
        if self._menu_visible:
            menu = self.query_one("#menu-container", HierarchicalMenu)
            menu.hide()
            self._menu_visible = False

    def action_show_help(self) -> None:
        help_text = self.slash_commands.get_help_text()
        help_text += "\n\nKeys: F1=Help F2=Menu F3=Game F10=Quit"
        self.notify(help_text, timeout=10)

    def _get_agent_zero_ui_url(self) -> str | None:
        connection = self.active_config.get("connection", {})
        ui_url = connection.get("ui_url") or connection.get("dashboard_url")
        if ui_url:
            return ui_url
        api_url = connection.get("api_url")
        if api_url:
            parsed = urlparse(api_url)
            base = parsed._replace(path="/", query="", fragment="")
            return urlunparse(base)
        host = connection.get("host")
        port = connection.get("port")
        if host and port:
            secure = connection.get("secure", False)
            scheme = "https" if secure else "http"
            return f"{scheme}://{host}:{port}/"
        return None

    def action_open_agent_ui(self) -> None:
        url = self._get_agent_zero_ui_url()
        if not url:
            self.notify("Agent Zero UI URL is not configured.", severity="warning")
            return
        webbrowser.open(url)
        self.notify(f"Opening Agent Zero UI: {url}")

    async def action_show_observer_settings(self) -> None:
        observer_config = self.active_config.get("observer", {})
        result = await self.push_screen_wait(
            ObserverConfigScreen(observer_config, self._get_agent_zero_ui_url())
        )
        if result == "open_ui":
            self.action_open_agent_ui()
        elif result == "edit_config":
            self.action_edit_config()

    def action_edit_config(self) -> None:
        config_path = Path("config.yaml").resolve()
        if not config_path.exists():
            self.notify("config.yaml not found", severity="warning")
            return
        webbrowser.open(config_path.as_uri())
        self.notify(f"Opening config: {config_path}")

    async def upload_file(self, source_path: str) -> str | None:
        src = Path(source_path).expanduser()
        if not src.exists() or not src.is_file():
            self.notify("File not found", severity="warning")
            return None

        workspace = self.active_config.get("connection", {}).get("workspace_root", ".")
        dest_root = Path(workspace).expanduser()
        dest_root.mkdir(parents=True, exist_ok=True)
        dest_dir = dest_root / "uploads"
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / src.name
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while True:
                candidate = dest_dir / f"{stem}-{counter}{suffix}"
                if not candidate.exists():
                    dest = candidate
                    break
                counter += 1

        await asyncio.to_thread(shutil.copy2, src, dest)
        self.notify(f"Uploaded to {dest}")
        return str(dest)

    async def action_show_file_upload(self) -> None:
        ws = self.active_config.get("connection", {}).get("workspace_root", "/")
        path = await self.push_screen_wait(FileUploadScreen(ws))
        if path:
            await self.upload_file(path)

    def action_push_game(self) -> None:
        self.push_screen(SpaceInvadersScreen())

    def action_new_chat_tab(self) -> None:
        self.create_new_chat_tab()

    def action_close_chat_tab(self) -> None:
        self.close_current_chat_tab()

    def create_new_chat_tab(self, name: str | None = None) -> None:
        count = self.session_manager.session_count() + 1
        session = self.session_manager.create_session(name or f"Chat {count}")
        self.session_manager.set_active(session.id)
        chat = self.query_one("#chat-container")
        chat.remove_children()
        chat.mount(Static(f"New chat: {session.name}", classes="status-msg"))
        self.notify(f"Created: {session.name}")

    def close_current_chat_tab(self) -> None:
        active = self.session_manager.get_active()
        if not active:
            return
        if self.session_manager.session_count() <= 1:
            self.notify("Cannot close the last tab", severity="warning")
            return
        self.session_manager.close_session(active.id)
        new_active = self.session_manager.get_active()
        if new_active:
            chat = self.query_one("#chat-container")
            chat.remove_children()
            chat.mount(Static(f"Switched to: {new_active.name}", classes="status-msg"))
        self.notify("Tab closed")

    def get_active_chat_container(self):
        return self.query_one("#chat-container")

    def on_hierarchical_menu_item_selected(self, event: HierarchicalMenu.ItemSelected) -> None:
        category, item_id = event.category, event.item_id
        if category == "project":
            self.action_switch_project(item_id)
        elif category == "agent":
            self.action_switch_agent_profile(item_id)
        elif category == "theme":
            self.action_switch_theme(item_id)
        elif category == "action":
            if item_id == "clear":
                self.run_worker(self.slash_commands._cmd_clear(self, []))
            elif item_id == "new_tab":
                self.create_new_chat_tab()
            elif item_id == "upload":
                self.run_worker(self.action_show_file_upload())
            elif item_id == "status":
                self.run_worker(self.slash_commands._cmd_status(self, []))
        elif category == "observer":
            self.run_worker(self.action_show_observer_settings())
        menu = self.query_one("#menu-container", HierarchicalMenu)
        menu.hide()

    def get_system_commands(self, screen):
        yield from super().get_system_commands(screen)
        yield SystemCommand("--- Projects ---", "", lambda: None)
        for name in sorted(self.projects.keys()):
            if name != self.current_project:
                yield SystemCommand(
                    f"  {name}",
                    "Switch to project",
                    lambda n=name: self.action_switch_project(n),
                )
        yield SystemCommand("--- Agents ---", "", lambda: None)
        for name in sorted(self.agent_profiles.keys()):
            if name != self.current_profile:
                yield SystemCommand(
                    f"  {name}",
                    "Switch to agent",
                    lambda n=name: self.action_switch_agent_profile(n),
                )
        yield SystemCommand("--- Themes ---", "", lambda: None)
        for name in THEME_PRESETS.keys():
            if name != self.theme_name:
                yield SystemCommand(
                    f"  {name}",
                    "Switch theme",
                    lambda n=name: self.action_switch_theme(n),
                )
