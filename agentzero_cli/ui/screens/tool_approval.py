"""Tool approval screen for AgentZeroCLI security interventions."""

import json
from typing import Any

from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ToolApprovalScreen(ModalScreen[str]):
    """Modal screen for approving/rejecting tool execution requests."""

    BINDINGS = [
        Binding("left", "focus_previous", "Left", show=False),
        Binding("right", "focus_next", "Right", show=False),
        Binding("y", "approve", "Approve", show=False),
        Binding("n", "reject", "Reject", show=False),
        Binding("e", "explain", "Explain", show=False),
    ]

    def __init__(
        self,
        tool_name: str,
        command: str,
        reason: str,
        backend: Any,
        tool_payload: dict[str, Any] | None = None,
    ):
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
            content = payload.get("content") or payload.get("text")
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
            preview = f"replace_text -> {path}\n--- OLD ---\n{old_text}\n--- NEW ---\n{new_text}"
            return preview.strip()

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
            cmd = payload.get("command") or self.command
            if not cmd:
                return ""
            return f"shell\n{cmd}".strip()

        if payload:
            try:
                payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
            except TypeError:
                payload_text = str(payload)
            return self._limit_lines(payload_text, 12)

        return ""

    def compose(self):
        with Container(id="dialog"):
            yield Label("AGENT ZERO: SECURITY INTERVENTION", id="risk-header")
            yield Label(f"\n[bold]Tool:[/] {self.tool_name}", markup=True)
            yield Label(f"[bold]Reason:[/] {self.reason}", markup=True)
            yield Static(f"$ {self.command}", id="command-box")

            preview = self._build_preview()
            if preview:
                with VerticalScroll(id="preview-container"):
                    yield Static(preview, id="preview-box")

            yield Static("", id="explanation-area", classes="explanation-text")

            with Horizontal(id="buttons-layout"):
                yield Button("Approve (Y)", classes="success", id="approve")
                yield Button("Explain (E)", classes="warning", id="explain")
                yield Button("Reject (N)", classes="error", id="reject")

    def on_mount(self) -> None:
        self.query_one("#explain").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "approve":
            self.dismiss("approved")
        elif btn_id == "reject":
            self.dismiss("rejected")
        elif btn_id == "explain":
            await self._show_explanation()

    async def _show_explanation(self) -> None:
        explanation = await self.backend.explain_risk(self.command)
        area = self.query_one("#explanation-area", Static)
        area.update(explanation)

    def action_approve(self) -> None:
        self.dismiss("approved")

    def action_reject(self) -> None:
        self.dismiss("rejected")

    async def action_explain(self) -> None:
        await self._show_explanation()
