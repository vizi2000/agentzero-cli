"""Tool approval workflow with security modes for CLI mode."""

import json
from typing import Any

# Tools that are auto-approved in "balanced" mode
READONLY_TOOLS = frozenset(
    {
        "read_file",
        "read",
        "list_files",
        "tree",
        "ls",
        "search_text",
        "search",
        "rg",
    }
)


class ToolApprovalHandler:
    """Handles tool approval workflow in CLI mode."""

    def __init__(self, renderer: Any, input_handler: Any, backend: Any):
        """Initialize approval handler.

        Args:
            renderer: OutputRenderer instance
            input_handler: InputHandler instance
            backend: RemoteAgentBackend instance
        """
        self.renderer = renderer
        self.input_handler = input_handler
        self.backend = backend

    @property
    def security_mode(self) -> str:
        """Get current security mode from backend."""
        return self.backend.security_mode

    def should_auto_approve(self, event: dict[str, Any]) -> bool:
        """Check if tool should be auto-approved.

        Rules:
        - god_mode: always approve
        - balanced: approve readonly tools only
        - paranoid: never auto-approve
        """
        if self.security_mode == "god_mode":
            return True
        if self.security_mode == "paranoid":
            return False
        # balanced mode
        tool_name = (event.get("tool_name") or "").lower()
        if tool_name in READONLY_TOOLS:
            return True
        if tool_name in ("terminal", "shell", "command"):
            return self._is_shell_whitelisted(event.get("command", ""))
        return False

    def _is_shell_whitelisted(self, command: str) -> bool:
        whitelist = getattr(self.backend, "whitelist", []) or []
        cmd = (command or "").strip().lower()
        for entry in whitelist:
            entry_text = str(entry).strip().lower()
            if entry_text and cmd.startswith(entry_text):
                return True
        return False

    async def request_approval(self, event: dict[str, Any]) -> str:
        """Request user approval for tool execution.

        Returns:
            "approved" or "rejected"
        """
        tool_name = event.get("tool_name", "tool")
        command = event.get("command", "")
        reason = event.get("reason", "No reason provided")
        payload = event.get("payload") or event

        # Check auto-approve first
        if self.should_auto_approve(event):
            self.renderer.approved(command, auto=True)
            return "approved"

        # Build preview for write operations
        preview = self._build_preview(tool_name, payload)

        # Render tool request
        self.renderer.tool_request(tool_name, command, reason, preview)

        # Interactive approval loop
        while True:
            choice = self.input_handler.get_approval()

            if choice == "a":
                self.renderer.approved(command)
                return "approved"

            if choice == "r":
                self.renderer.rejected(command)
                return "rejected"

            if choice == "e":
                await self._show_explanation(command)
                # Loop continues

    async def _show_explanation(self, command: str) -> None:
        """Show AI risk explanation."""
        self.renderer.status("Analyzing risk...")
        explanation = await self.backend.explain_risk(command)
        self.renderer.info(explanation)

    def _build_preview(self, tool_name: str, payload: dict[str, Any]) -> str | None:
        """Build preview text for tool request."""
        tool_name = tool_name.lower()

        if tool_name in ("write_file", "file_write"):
            path = payload.get("path") or payload.get("file") or payload.get("target") or ""
            content = payload.get("content") or payload.get("text")
            if content is None:
                return None
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            preview = self._limit_lines(content, 12)
            return f"write_file -> {path}\n{preview}".strip()

        if tool_name in ("replace_text", "replace"):
            path = payload.get("path") or payload.get("file") or payload.get("target") or ""
            old = payload.get("old") or payload.get("find")
            new = payload.get("new") or payload.get("replace")
            if old is None or new is None:
                return None
            old_text = self._truncate(str(old), 200)
            new_text = self._truncate(str(new), 200)
            preview = f"replace_text -> {path}\n--- OLD ---\n{old_text}\n--- NEW ---\n{new_text}"
            return preview.strip()

        if tool_name in ("apply_patch", "patch"):
            patch_text = payload.get("patch") or payload.get("diff")
            if not patch_text:
                return None
            preview = self._limit_lines(str(patch_text), 16)
            return f"apply_patch\n{preview}".strip()

        if tool_name in ("terminal", "shell", "command"):
            cmd = payload.get("command")
            if not cmd:
                return None
            return f"shell\n{cmd}".strip()

        return None

    def _truncate(self, text: str, limit: int) -> str:
        """Truncate text to limit."""
        if len(text) <= limit:
            return text
        return f"{text[:limit]}... (truncated)"

    def _limit_lines(self, text: str, max_lines: int) -> str:
        """Limit text to max lines."""
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return text
        trimmed = lines[:max_lines]
        trimmed.append(f"... ({len(lines) - max_lines} more lines)")
        return "\n".join(trimmed)
