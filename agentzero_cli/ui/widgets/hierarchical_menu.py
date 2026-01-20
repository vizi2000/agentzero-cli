"""Hierarchical menu widget for AgentZeroCLI."""

from typing import Any

from textual.containers import Container
from textual.message import Message
from textual.widgets import Tree


class HierarchicalMenu(Container):
    """Hierarchical menu with categories for Projects, Agents, Themes, Settings."""

    class ItemSelected(Message):
        """Posted when a menu item is selected."""

        def __init__(self, category: str, item_id: str, item_label: str) -> None:
            self.category = category
            self.item_id = item_id
            self.item_label = item_label
            super().__init__()

    DEFAULT_CSS = """
    HierarchicalMenu {
        dock: left;
        width: 32;
        height: 100%;
        background: $surface;
        border-right: solid $primary;
        layer: menu;
    }
    HierarchicalMenu.hidden {
        display: none;
    }
    HierarchicalMenu Tree {
        padding: 1;
        scrollbar-gutter: stable;
    }
    HierarchicalMenu Tree:focus {
        border: solid $primary;
    }
    """

    def __init__(
        self,
        projects: dict[str, Any],
        agents: dict[str, Any],
        themes: list[str],
        current_project: str = "",
        current_agent: str = "",
        current_theme: str = "",
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self._projects = projects
        self._agents = agents
        self._themes = themes
        self._current_project = current_project
        self._current_agent = current_agent
        self._current_theme = current_theme

    def compose(self):
        tree = Tree("Menu", id="main-menu")
        tree.root.expand()

        # Projects category
        projects_node = tree.root.add("Projects", expand=True)
        for name in sorted(self._projects.keys()):
            marker = " *" if name == self._current_project else ""
            projects_node.add_leaf(f"{name}{marker}", data=("project", name))

        # Agents category
        agents_node = tree.root.add("Agents", expand=True)
        for name in sorted(self._agents.keys()):
            marker = " *" if name == self._current_agent else ""
            agents_node.add_leaf(f"{name}{marker}", data=("agent", name))

        # Themes category
        themes_node = tree.root.add("Themes", expand=False)
        for name in self._themes:
            marker = " *" if name == self._current_theme else ""
            themes_node.add_leaf(f"{name}{marker}", data=("theme", name))

        # Actions category
        actions_node = tree.root.add("Actions", expand=True)
        actions_node.add_leaf("Clear Chat", data=("action", "clear"))
        actions_node.add_leaf("New Tab", data=("action", "new_tab"))
        actions_node.add_leaf("Upload File", data=("action", "upload"))
        actions_node.add_leaf("Show Status", data=("action", "status"))
        actions_node.add_leaf("Observer Settings", data=("observer", "config"))

        yield tree

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if node.data:
            category, item_id = node.data
            self.post_message(self.ItemSelected(category, item_id, str(node.label)))
            event.stop()  # Stop event propagation

    def update_current(
        self,
        project: str | None = None,
        agent: str | None = None,
        theme: str | None = None,
    ) -> None:
        """Update current selections and refresh display."""
        if project is not None:
            self._current_project = project
        if agent is not None:
            self._current_agent = agent
        if theme is not None:
            self._current_theme = theme
        # Re-compose to update markers
        self.remove_children()
        self.mount(*self.compose())

    def toggle(self) -> None:
        """Toggle menu visibility."""
        self.toggle_class("hidden")
        # Focus the tree when showing menu
        if not self.has_class("hidden"):
            self.call_after_refresh(self._focus_tree)

    def _focus_tree(self) -> None:
        """Focus the tree widget after refresh."""
        try:
            tree = self.query_one("#main-menu", Tree)
            tree.focus()
        except Exception:
            pass

    def show(self) -> None:
        """Show the menu."""
        self.remove_class("hidden")
        self.call_after_refresh(self._focus_tree)

    def hide(self) -> None:
        """Hide the menu."""
        self.add_class("hidden")
