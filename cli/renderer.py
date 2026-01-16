"""Rich-based terminal output rendering for CLI mode."""

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


class OutputRenderer:
    """Renders output to terminal using Rich library."""

    def __init__(self, console: Console):
        self.console = console

    def header(self, url: str, project: str, mode: str) -> None:
        """Render connection header box."""
        content = f"{url} | {project} | {mode}"
        panel = Panel(
            content,
            title="Agent Zero",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        self.console.print(panel)
        self.console.print()

    def user_message(self, text: str) -> None:
        """Render user input message."""
        self.console.print(f"[bold blue]> {text}[/]")
        self.console.print()

    def agent_response(self, text: str) -> None:
        """Render agent response with markdown."""
        self.console.print()
        md = Markdown(text)
        self.console.print(md)
        self.console.print()

    def agent_streaming(self, text: str) -> None:
        """Render streaming text chunk (no newline)."""
        self.console.print(text, end="", highlight=False)

    def thinking(self, text: str) -> None:
        """Render thinking/status message."""
        if len(text) > 100:
            text = text[:100] + "..."
        self.console.print(f"[dim italic]{text}[/]")

    def status(self, text: str) -> None:
        """Render status message."""
        self.console.print(f"[dim]{text}[/]")

    def tool_request(
        self, name: str, command: str, reason: str, preview: str | None = None
    ) -> None:
        """Render tool request box."""
        content = f"[bold yellow]{name}:[/] {command}\n[dim]Reason:[/] {reason}"
        if preview:
            content += f"\n\n[dim]{preview}[/]"
        panel = Panel(
            content,
            title="Tool Request",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        self.console.print(panel)

    def tool_output(self, text: str) -> None:
        """Render tool execution output."""
        if len(text) > 2000:
            text = text[:2000] + "\n... [truncated]"
        self.console.print(f"[dim]{text}[/]")

    def approved(self, command: str, auto: bool = False) -> None:
        """Render approval confirmation."""
        prefix = "AUTO-" if auto else ""
        self.console.print(f"[green]✓ {prefix}Approved: {command}[/]")
        self.console.print()

    def rejected(self, command: str) -> None:
        """Render rejection."""
        self.console.print(f"[red]✗ Rejected: {command}[/]")
        self.console.print()

    def error(self, text: str) -> None:
        """Render error message."""
        self.console.print(f"[bold red]Error: {text}[/]")

    def info(self, text: str) -> None:
        """Render info message."""
        self.console.print(f"[cyan]{text}[/]")

    def goodbye(self) -> None:
        """Render goodbye message."""
        self.console.print("[dim]Goodbye![/]")

    def news_item(self, item: dict) -> None:
        """Render news item during waiting."""
        title = item.get("title", "")[:60]
        source = item.get("source", "")
        url = item.get("url", "")
        if source and url:
            self.console.print(f"[dim]📰 {title}[/]")
            self.console.print(f"[dim]   {source} → {url}[/]")
        else:
            # Fallback tip (no source/url)
            self.console.print(f"[dim]💡 {title}[/]")
