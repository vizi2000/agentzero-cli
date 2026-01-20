"""Chat tab management widget for AgentZeroCLI."""

from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, TabbedContent, TabPane

from .session import ChatSession, SessionManager


class ChatTabBar(Widget):
    """Tab bar for managing multiple chat sessions."""

    class TabChanged(Message):
        """Posted when active tab changes."""

        def __init__(self, session_id: str) -> None:
            self.session_id = session_id
            super().__init__()

    class NewTabRequested(Message):
        """Posted when new tab is requested."""

        pass

    class TabCloseRequested(Message):
        """Posted when tab close is requested."""

        def __init__(self, session_id: str) -> None:
            self.session_id = session_id
            super().__init__()

    def __init__(
        self,
        session_manager: SessionManager,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.session_manager = session_manager

    def compose(self):
        with Horizontal(id="chat-tabs-bar"):
            yield TabbedContent(id="chat-tabs")
            yield Button("+", id="new-tab-btn", classes="tab-button")

    def on_mount(self) -> None:
        self._sync_tabs()

    def _sync_tabs(self) -> None:
        """Synchronize tabs with session manager."""
        tabs = self.query_one("#chat-tabs", TabbedContent)

        # Add tabs for each session
        for session in self.session_manager.list_sessions():
            tab_id = f"tab-{session.id}"
            try:
                tabs.query_one(f"#{tab_id}")
            except Exception:
                # Tab doesn't exist, create it
                pane = TabPane(session.name, id=tab_id)
                tabs.add_pane(pane)

        # Set active tab
        active = self.session_manager.get_active()
        if active:
            tabs.active = f"tab-{active.id}"

    def add_tab(self, session: ChatSession) -> None:
        """Add a new tab for the session."""
        tabs = self.query_one("#chat-tabs", TabbedContent)
        tab_id = f"tab-{session.id}"
        pane = TabPane(session.name, id=tab_id)
        tabs.add_pane(pane)
        tabs.active = tab_id
        self.session_manager.set_active(session.id)
        self.post_message(self.TabChanged(session.id))

    def close_tab(self, session_id: str) -> bool:
        """Close and remove a tab."""
        if not self.session_manager.close_session(session_id):
            return False

        tabs = self.query_one("#chat-tabs", TabbedContent)
        tab_id = f"tab-{session_id}"
        try:
            tabs.remove_pane(tab_id)
        except Exception:
            pass

        # Update active
        active = self.session_manager.get_active()
        if active:
            tabs.active = f"tab-{active.id}"
            self.post_message(self.TabChanged(active.id))

        return True

    def rename_tab(self, session_id: str, new_name: str) -> None:
        """Rename a tab."""
        self.session_manager.rename_session(session_id, new_name)
        # TabPane title update requires re-sync
        self._sync_tabs()

    def get_active_session_id(self) -> str | None:
        """Get ID of currently active session."""
        active = self.session_manager.get_active()
        return active.id if active else None

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab activation."""
        tab_id = str(event.tab.id)
        if tab_id.startswith("tab-"):
            session_id = tab_id[4:]  # Remove "tab-" prefix
            self.session_manager.set_active(session_id)
            self.post_message(self.TabChanged(session_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "new-tab-btn":
            self.post_message(self.NewTabRequested())
