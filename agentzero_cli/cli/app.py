"""Main CLI application loop for AgentZeroCLI."""

import sys
from pathlib import Path

import yaml
from rich.console import Console

from ..backend import get_backend

from .approval import ToolApprovalHandler
from .commands import CLISlashCommands
from .input import InputHandler
from .renderer import OutputRenderer
from .setup_wizard import check_and_run_wizard


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file (auto-detects if None)

    Returns:
        Config dict (empty dict if file not found)
    """
    if config_path:
        paths_to_try = [Path(config_path)]
    else:
        paths_to_try = [
            Path("config.yaml"),
            Path.home() / ".config" / "agentzero" / "config.yaml",
        ]

    for path in paths_to_try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict, config_path: str = "config.yaml") -> None:
    """Save configuration to YAML file.

    Args:
        config: Config dict to save
        config_path: Path to config file
    """
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


class CLIApp:
    """Main CLI application - Claude Code-like interface for Agent Zero."""

    def __init__(self, config_path: str = None):
        """Initialize CLI application.

        Args:
            config_path: Path to config.yaml (auto-detected if None)
        """
        self.console = Console()

        if config_path:
            self.config_path = config_path
        else:
            resolved_path = check_and_run_wizard(self.console)
            if resolved_path is None:
                self.console.print("[red]Configuration required. Exiting.[/]")
                sys.exit(1)
            self.config_path = str(resolved_path)

        self.config = load_config(self.config_path)
        self.renderer = OutputRenderer(self.console)

        # Initialize backend using factory
        self.backend = get_backend()

        # Initialize components
        workspace = getattr(self.backend, 'workspace_root', str(Path.cwd()))
        self.input_handler = InputHandler(workspace)
        self.commands = CLISlashCommands()

        # Connect commands to input completer
        self.input_handler.set_commands(self.commands.commands)

        self.approval = ToolApprovalHandler(
            self.renderer,
            self.input_handler,
            self.backend,
        )

        self.running = True

    async def run(self) -> None:
        """Main application loop."""
        # Show header
        self.renderer.header(
            self.backend.api_url or "not configured",
            self.backend.project_name,
            self.backend.security_mode,
        )

        # Main loop
        while self.running:
            try:
                user_input = await self.input_handler.get_input("> ")

                if not user_input:
                    continue

                # Check for slash commands
                if await self.commands.execute(self, user_input):
                    continue

                # Process as agent message
                await self.handle_message(user_input)

            except KeyboardInterrupt:
                self.renderer.goodbye()
                break
            except EOFError:
                self.renderer.goodbye()
                break
            except Exception as e:
                self.renderer.error(str(e))

    async def handle_message(self, text: str) -> None:
        """Send message to agent and handle response.

        Args:
            text: User message text
        """
        # Show user message
        self.renderer.user_message(text)

        # Stream events from backend
        try:
            with self.console.status("[bold cyan]Thinking...", spinner="dots"):
                async for event in self.backend.send_prompt(text):
                    await self._process_event(event)
        except Exception as e:
            self.renderer.error(f"Connection error: {e}")

    async def _process_event(self, event: dict) -> None:
        """Process a single event from backend.

        Event types:
        - status: Connection/processing status
        - thinking/thought: Agent reasoning
        - final_response: Agent's response
        - tool_output: Tool execution output
        - tool_request: Tool approval request
        """
        event_type = event.get("type", "")
        content = event.get("content", "")

        if event_type == "status":
            # Filter keepalive spam, show news instead
            if "Oczekiwanie na odpowiedź" in content:
                from .news import get_random_news

                item = get_random_news()
                if item:
                    self.renderer.news_item(item)
                return
            self.renderer.status(content)

        elif event_type in ("thinking", "thought"):
            self.renderer.thinking(content)

        elif event_type == "final_response":
            self.renderer.agent_response(content)

        elif event_type == "tool_output":
            self.renderer.tool_output(content)

        elif event_type == "tool_request":
            await self._handle_tool_request(event)

    async def _handle_tool_request(self, event: dict) -> None:
        """Handle tool approval and execution.

        Args:
            event: Tool request event
        """
        # Request approval
        decision = await self.approval.request_approval(event)

        if decision == "approved":
            # Execute tool
            with self.console.status("[bold cyan]Executing...", spinner="dots"):
                async for exec_event in self.backend.execute_tool(event):
                    await self._process_event(exec_event)
        else:
            with self.console.status("[bold yellow]Rejected...", spinner="dots"):
                if hasattr(self.backend, "reject_tool"):
                    async for exec_event in self.backend.reject_tool(event):
                        await self._process_event(exec_event)
