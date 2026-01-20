"""File upload screen for AgentZeroCLI."""

from pathlib import Path

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Static


class FileUploadScreen(ModalScreen[str | None]):
    """File picker and upload screen.

    Returns the selected file path or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FileUploadScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #upload-dialog {
        width: 80;
        height: 30;
        border: heavy $primary;
        background: $surface;
        padding: 1;
    }
    #upload-header {
        height: 2;
        text-align: center;
        text-style: bold;
        color: $primary;
    }
    #file-tree {
        height: 1fr;
        border: solid $primary-darken-2;
        background: $background;
        margin: 1 0;
    }
    #path-input {
        margin-bottom: 1;
    }
    #upload-buttons {
        height: 3;
        align: center middle;
    }
    #upload-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: str = "/"):
        super().__init__()
        self.start_path = start_path
        self.selected_file: str | None = None

    def compose(self):
        with Vertical(id="upload-dialog"):
            yield Static("Select file to upload to workspace", id="upload-header")
            yield DirectoryTree(self.start_path, id="file-tree")
            yield Input(placeholder="Or enter file path...", id="path-input")
            with Horizontal(id="upload-buttons"):
                yield Button("Upload", id="upload-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in tree."""
        self.selected_file = str(event.path)
        self.query_one("#path-input", Input).value = self.selected_file

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle manual path input."""
        if event.input.id == "path-input":
            self.selected_file = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "upload-btn":
            path = self.query_one("#path-input", Input).value or self.selected_file
            if path and Path(path).is_file():
                self.dismiss(path)
            else:
                self.notify("Please select a valid file", severity="warning")
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)
