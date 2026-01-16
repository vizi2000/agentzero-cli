import asyncio
import fnmatch
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from datetime import datetime
from typing import Any


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


class MockAgentBackend:
    """
    Klasa symulująca zachowanie Agenta Zero po drugiej stronie sieci.
    Docelowo ta klasa zostanie zastąpiona klientem WebSocket/HTTP.
    """

    async def send_prompt(self, user_text: str):
        """Symuluje wysłanie promptu do agenta i otrzymanie strumienia myśli."""
        yield {"type": "status", "content": "Łączenie z Agentem..."}
        await asyncio.sleep(0.5)

        yield {"type": "status", "content": "Agent analizuje zadanie..."}
        await asyncio.sleep(1.0)

        thoughts = [
            f"Użytkownik prosi o: '{user_text}'.",
            "Analizuję strukturę plików w katalogu roboczym...",
            "Wykryłem stare pliki tymczasowe w ./build.",
            "Muszę wyczyścić środowisko przed rozpoczęciem pracy.",
        ]

        for thought in thoughts:
            yield {"type": "thought", "content": thought}
            await asyncio.sleep(0.8)

        yield {
            "type": "tool_request",
            "tool_name": "terminal",
            "command": "rm -rf ./build/*",
            "reason": "Wymagane czyszczenie cache przed kompilacją.",
            "risk_level": "high",
        }

    async def explain_risk(self, command: str):
        await asyncio.sleep(1.5)
        return (
            "[bold yellow]ANALIZA AI:[/]\n"
            f"Komenda [i]{command}[/i] trwale usuwa pliki bez przenoszenia do kosza.\n"
            "W kontekście Twojego projektu, katalog [i]./build[/i] zawiera tylko pliki "
            "generowane automatycznie.\n"
            "[bold green]WERDYKT:[/b] Bezpieczne, jeśli nie trzymasz tam kodu źródłowego."
        )

    async def execute_tool(self, tool_event: Any):
        command = tool_event
        if isinstance(tool_event, dict):
            command = tool_event.get("command") or tool_event.get("summary") or "tool"
        yield {"type": "status", "content": f"Wykonywanie: {command}..."}
        await asyncio.sleep(1.0)
        yield {"type": "tool_output", "content": "Deleted 42 files.\nDirectory cleaned."}
        yield {"type": "final_response", "content": "Zadanie wykonane. Środowisko jest czyste."}

    async def reject_tool(self, tool_event: Any, reason: str = "rejected by user"):
        command = tool_event
        if isinstance(tool_event, dict):
            command = tool_event.get("command") or tool_event.get("summary") or "tool"
        yield {"type": "status", "content": f"Tool rejected: {command}"}


class RemoteAgentBackend:
    def __init__(self, config: dict[str, Any]):
        connection = config.get("connection", {})
        self.api_url = self._resolve_api_url(connection)
        self.logger = logging.getLogger("agentzero.backend")
        self.api_key = os.environ.get("AGENTZERO_API_KEY") or connection.get("api_key")
        self.lifetime_hours = _coerce_int(
            os.environ.get("AGENTZERO_LIFETIME_HOURS", connection.get("lifetime_hours", 24)),
            24,
        )
        self.timeout_seconds = _coerce_float(
            os.environ.get("AGENTZERO_TIMEOUT_SECONDS", connection.get("timeout_seconds", 30)),
            30.0,
        )
        self.context_id: str | None = None
        self.workspace_root = os.path.abspath(
            os.environ.get(
                "AGENTZERO_WORKSPACE_ROOT",
                connection.get("workspace_root") or os.getcwd(),
            )
        )
        self.send_tool_results = _coerce_bool(
            os.environ.get("AGENTZERO_SEND_TOOL_RESULTS"),
            connection.get("send_tool_results", True),
        )
        self.stream_enabled = _coerce_bool(
            os.environ.get("AGENTZERO_STREAM"),
            connection.get("stream", False),
        )
        self.stream_mode = os.environ.get("AGENTZERO_STREAM_MODE") or connection.get(
            "stream_mode", "auto"
        )
        self.keepalive_seconds = _coerce_float(
            os.environ.get("AGENTZERO_KEEPALIVE_SECONDS", connection.get("keepalive_seconds", 5)),
            5.0,
        )
        self.max_wait_seconds = _coerce_float(
            os.environ.get("AGENTZERO_MAX_WAIT_SECONDS", connection.get("max_wait_seconds", 0)),
            0.0,
        )
        self.project_name = (
            os.environ.get("AGENTZERO_PROJECT")
            or config.get("active_project")
            or config.get("project_name")
            or "default"
        )
        context_cfg = config.get("context", {})
        self.context_enabled = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT"),
            context_cfg.get("enabled", True),
        )
        self.context_mode = (
            os.environ.get("AGENTZERO_CONTEXT_MODE") or context_cfg.get("mode", "on_change")
        ).lower()
        self.context_max_bytes = _coerce_int(
            os.environ.get("AGENTZERO_CONTEXT_MAX_BYTES", context_cfg.get("max_bytes", 20000)),
            20000,
        )
        self.context_max_files = _coerce_int(
            os.environ.get("AGENTZERO_CONTEXT_MAX_FILES", context_cfg.get("max_files", 200)),
            200,
        )
        self.context_max_depth = _coerce_int(
            os.environ.get("AGENTZERO_CONTEXT_MAX_DEPTH", context_cfg.get("max_depth", 4)),
            4,
        )
        self.context_include_tree = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT_TREE"),
            context_cfg.get("include_tree", True),
        )
        self.context_include_previews = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT_PREVIEWS"),
            context_cfg.get("include_previews", True),
        )
        self.context_preview_files = context_cfg.get("preview_files")
        self.context_max_preview_bytes = _coerce_int(
            os.environ.get(
                "AGENTZERO_CONTEXT_MAX_PREVIEW_BYTES",
                context_cfg.get("max_preview_bytes", 6000),
            ),
            6000,
        )
        self.context_include_git = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT_GIT"),
            context_cfg.get("include_git", True),
        )
        self.context_include_system = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT_SYSTEM"),
            context_cfg.get("include_system", True),
        )
        self.context_include_tools = _coerce_bool(
            os.environ.get("AGENTZERO_CONTEXT_TOOLS"),
            context_cfg.get("include_tools", True),
        )
        redact_keys = context_cfg.get(
            "redact_keys",
            [
                "api_key",
                "apikey",
                "token",
                "secret",
                "password",
                "private_key",
                "access_key",
                "auth",
                "authorization",
            ],
        )
        if isinstance(redact_keys, str):
            redact_keys = [redact_keys]
        self.context_redact_keys = [str(key) for key in redact_keys if key]
        redact_patterns = context_cfg.get("redact_patterns", [])
        if isinstance(redact_patterns, str):
            redact_patterns = [redact_patterns]
        self.context_redact_patterns = [str(pattern) for pattern in redact_patterns if pattern]
        self.context_ignore_dirs = context_cfg.get(
            "ignore_dirs",
            [
                ".git",
                "venv",
                "__pycache__",
                "node_modules",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".idea",
                ".vscode",
                ".snapshots",
            ],
        )
        self._context_signature: str | None = None
        self._last_context_meta: dict[str, Any] | None = None
        observer_cfg = config.get("observer", {})
        self.observer_enabled = _coerce_bool(
            os.environ.get("AGENTZERO_OBSERVER_ENABLED"),
            observer_cfg.get("enabled", False),
        )
        self.observer_mode = str(observer_cfg.get("mode", "automatic")).lower()
        self._observer_signature: str | None = None
        self._observer_meta: dict[str, Any] | None = None
        security = config.get("security", {})
        self.security_mode = security.get("mode", "balanced")
        self.whitelist = security.get("whitelist", [])
        self.blacklist_patterns = security.get("blacklist_patterns", [])
        self.allow_shell = _coerce_bool(
            os.environ.get("AGENTZERO_ALLOW_SHELL"),
            security.get("allow_shell", False),
        )
        if self.allow_shell:
            self.logger.warning("Shell execution enabled (allow_shell=true).")
        (
            self.agent_profile_name,
            self.agent_profile_prompt,
        ) = self._resolve_agent_profile(config)

    async def send_prompt(self, user_text: str):
        if not self.api_url:
            yield {
                "type": "final_response",
                "content": "Brak api_url w konfiguracji połączenia.",
            }
            return

        yield {"type": "status", "content": "Łączenie z Agentem Zero..."}
        self.logger.debug("Preparing prompt len=%d stream=%s", len(user_text), self.stream_enabled)
        message, context_included, observer_included = self._prepare_message(user_text)
        if observer_included:
            summary = self._format_observer_status()
            if summary:
                yield {"type": "status", "content": summary}
        if context_included:
            summary = self._format_context_status()
            if summary:
                yield {"type": "status", "content": summary}
        payload = {"message": message, "lifetime_hours": self.lifetime_hours}
        if self.context_id:
            payload["context_id"] = self.context_id

        async for event in self._run_request(payload, allow_stream=self.stream_enabled):
            yield event

    async def explain_risk(self, command: str):
        if not command:
            return "Brak komendy do analizy ryzyka."

        pattern = self._matches_blacklist(command)
        if pattern:
            return (
                "[bold red]WYSOKIE RYZYKO:[/]\n"
                f"Wykryto blokowany wzorzec: [i]{pattern}[/i].\n"
                "Zalecane odrzucenie."
            )

        lowered = command.lower()
        if any(token in lowered for token in ("patch", "write_file", "replace_text")):
            return (
                "[bold yellow]ŚREDNIE RYZYKO:[/]\n"
                "Operacja modyfikuje pliki w workspace.\n"
                "Zweryfikuj ścieżkę i treść zmian."
            )

        if any(token in lowered for token in ("rm ", "del ", "format", "mkfs")):
            return (
                "[bold red]WYSOKIE RYZYKO:[/]\n" "Polecenie może usuwać dane lub formatować dysk."
            )

        return "[bold green]NISKIE RYZYKO:[/] Brak oczywistych zagrożeń."

    async def execute_tool(self, tool_event: Any):
        tool = self._coerce_tool_event(tool_event)
        tool_name = tool.get("tool_name") or tool.get("name") or "tool"
        tool_call_id = tool.get("tool_call_id") or tool.get("id")
        command = tool.get("command") or tool.get("summary")

        if tool_name in ("read_file", "read"):
            events, result = self._handle_read_file(tool, tool_name, tool_call_id)
        elif tool_name in ("list_files", "tree", "ls"):
            events, result = self._handle_list_files(tool, tool_name, tool_call_id)
        elif tool_name in ("search_text", "search", "rg"):
            events, result = self._handle_search_text(tool, tool_name, tool_call_id)
        elif tool_name in ("write_file", "file_write"):
            events, result = self._handle_write_file(tool, tool_name, tool_call_id)
        elif tool_name in ("replace_text", "replace"):
            events, result = self._handle_replace_text(tool, tool_name, tool_call_id)
        elif tool_name in ("apply_patch", "patch"):
            events, result = self._handle_apply_patch(tool, tool_name, tool_call_id)
        elif tool_name in ("terminal", "shell", "command"):
            events, result = await self._handle_shell(tool, tool_name, tool_call_id)
        else:
            message = f"Nieobsługiwane narzędzie: {tool_name}"
            events = [{"type": "final_response", "content": message}]
            result = self._make_tool_result(
                tool_name,
                False,
                message,
                {"command": command},
                tool_call_id,
            )

        for item in events:
            yield item

        if self.send_tool_results:
            async for item in self._post_tool_result(result):
                yield item

    async def reject_tool(self, tool_event: Any, reason: str = "rejected by user"):
        tool = self._coerce_tool_event(tool_event)
        tool_name = tool.get("tool_name") or tool.get("name") or "tool"
        tool_call_id = tool.get("tool_call_id") or tool.get("id")
        command = tool.get("command") or tool.get("summary")
        message = f"Tool rejected: {command}".strip()
        self.logger.debug("Tool rejected: %s reason=%s", tool_name, reason)
        yield {"type": "status", "content": message}
        result = self._make_tool_result(
            tool_name,
            False,
            reason,
            {"command": command, "reason": reason},
            tool_call_id,
        )
        if self.send_tool_results:
            async for item in self._post_tool_result(result):
                yield item

    def _handle_read_file(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        path = tool.get("path") or tool.get("file") or tool.get("target")
        start_line = tool.get("start_line")
        end_line = tool.get("end_line")
        max_bytes = _coerce_int(
            tool.get("max_bytes", self.context_max_preview_bytes),
            self.context_max_preview_bytes,
        )

        if not path:
            message = "Brak path w read_file."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        try:
            full_path = self._resolve_safe_path(path)
        except ValueError as exc:
            message = f"read_file zablokowane: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if not os.path.exists(full_path):
            message = f"Plik nie istnieje: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if os.path.isdir(full_path):
            message = f"To jest katalog, nie plik: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        truncated = False
        try:
            with open(full_path, encoding="utf-8", errors="replace") as handle:
                if start_line is not None or end_line is not None:
                    lines = handle.readlines()
                    start_idx = max(0, _coerce_int(start_line, 1) - 1)
                    end_idx = _coerce_int(end_line, len(lines))
                    if end_idx <= 0:
                        end_idx = len(lines)
                    content = "".join(lines[start_idx:end_idx])
                else:
                    if max_bytes and max_bytes > 0:
                        content = handle.read(max_bytes + 1)
                    else:
                        content = handle.read()
        except OSError as exc:
            message = f"Nie mogę odczytać pliku: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if max_bytes and max_bytes > 0 and len(content) > max_bytes:
            content = content[:max_bytes] + "\n... [truncated]"
            truncated = True

        self.logger.debug("Read %s (%s bytes)", path, len(content))
        events.append({"type": "tool_output", "content": content})
        events.append({"type": "final_response", "content": "Odczyt zakończony."})
        result = self._make_tool_result(
            tool_name,
            True,
            "read_file ok",
            {
                "path": path,
                "bytes": len(content),
                "truncated": truncated,
                "start_line": start_line,
                "end_line": end_line,
            },
            tool_call_id,
        )
        return events, result

    def _handle_list_files(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        path = tool.get("path") or tool.get("dir") or "."
        max_depth = _coerce_int(
            tool.get("max_depth", self.context_max_depth),
            self.context_max_depth,
        )
        max_files = _coerce_int(
            tool.get("max_files", self.context_max_files),
            self.context_max_files,
        )
        include_sizes = _coerce_bool(tool.get("include_sizes", True), True)

        try:
            full_root = self._resolve_safe_path(path)
        except ValueError as exc:
            message = f"list_files zablokowane: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if not os.path.exists(full_root):
            message = f"Katalog nie istnieje: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if not os.path.isdir(full_root):
            message = f"To nie jest katalog: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        ignore = set(self.context_ignore_dirs)
        output_lines: list[str] = []
        total_files = 0
        truncated = False
        for dirpath, dirnames, filenames in os.walk(full_root):
            rel_dir = os.path.relpath(dirpath, full_root)
            depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
            dirnames[:] = [d for d in dirnames if d not in ignore]
            if depth >= max_depth:
                dirnames[:] = []
            for name in sorted(filenames):
                if total_files >= max_files:
                    truncated = True
                    break
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, self.workspace_root)
                entry = rel_path
                if include_sizes:
                    try:
                        size = os.path.getsize(full_path)
                        entry = f"{entry} ({size}B)"
                    except OSError:
                        pass
                output_lines.append(entry)
                total_files += 1
            if truncated:
                break

        if truncated:
            output_lines.append("... [truncated]")

        output = "\n".join(output_lines)
        if not output:
            output = "(no files)"
        events.append({"type": "tool_output", "content": output})
        events.append({"type": "final_response", "content": "Lista plików gotowa."})
        result = self._make_tool_result(
            tool_name,
            True,
            f"listed {total_files} files",
            {"path": path, "files": total_files, "truncated": truncated},
            tool_call_id,
        )
        return events, result

    def _handle_search_text(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        query = tool.get("query") or tool.get("pattern") or tool.get("text")
        path = tool.get("path") or "."
        max_matches = _coerce_int(tool.get("max_matches", 50), 50)
        max_files = _coerce_int(tool.get("max_files", 2000), 2000)
        max_file_bytes = _coerce_int(tool.get("max_file_bytes", 200000), 200000)
        case_sensitive = _coerce_bool(tool.get("case_sensitive", False), False)

        if not query:
            message = "Brak query w search_text."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        try:
            full_root = self._resolve_safe_path(path)
        except ValueError as exc:
            message = f"search_text zablokowane: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if not os.path.exists(full_root):
            message = f"Ścieżka nie istnieje: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        query_cmp = query if case_sensitive else str(query).lower()
        ignore = set(self.context_ignore_dirs)
        matches: list[str] = []
        files_scanned = 0

        for dirpath, dirnames, filenames in os.walk(full_root):
            dirnames[:] = [d for d in dirnames if d not in ignore]
            for name in filenames:
                if files_scanned >= max_files or len(matches) >= max_matches:
                    break
                full_path = os.path.join(dirpath, name)
                try:
                    if os.path.getsize(full_path) > max_file_bytes:
                        continue
                except OSError:
                    continue
                rel_path = os.path.relpath(full_path, self.workspace_root)
                try:
                    with open(full_path, encoding="utf-8", errors="replace") as handle:
                        for idx, line in enumerate(handle, start=1):
                            hay = line if case_sensitive else line.lower()
                            if query_cmp in hay:
                                matches.append(f"{rel_path}:{idx}: {line.rstrip()}")
                                if len(matches) >= max_matches:
                                    break
                except OSError:
                    continue
                files_scanned += 1
            if files_scanned >= max_files or len(matches) >= max_matches:
                break

        output = "\n".join(matches) if matches else "(no matches)"
        events.append({"type": "tool_output", "content": output})
        events.append({"type": "final_response", "content": "Wyszukiwanie zakończone."})
        result = self._make_tool_result(
            tool_name,
            True,
            f"matches: {len(matches)}",
            {
                "query": query,
                "path": path,
                "matches": len(matches),
                "files_scanned": files_scanned,
            },
            tool_call_id,
        )
        return events, result

    def _handle_write_file(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        path = tool.get("path") or tool.get("file") or tool.get("target")
        content = tool.get("content")
        if content is None and "text" in tool:
            content = tool.get("text")

        if not path or content is None:
            message = "Brak path/content w write_file."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)

        try:
            full_path = self._resolve_safe_path(path)
        except ValueError as exc:
            message = f"write_file zablokowane: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        os.makedirs(os.path.dirname(full_path) or self.workspace_root, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as handle:
            handle.write(content)

        output = f"Zapisano: {path} ({len(content)} chars)"
        events.append({"type": "tool_output", "content": output})
        events.append({"type": "final_response", "content": "Zapis zakończony."})
        result = self._make_tool_result(
            tool_name,
            True,
            output,
            {"path": path, "bytes": len(content)},
            tool_call_id,
        )
        return events, result

    def _handle_replace_text(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        path = tool.get("path") or tool.get("file") or tool.get("target")
        old = tool.get("old") or tool.get("find")
        new = tool.get("new") or tool.get("replace")
        count = tool.get("count")

        if not path or old is None or new is None:
            message = "Brak path/old/new w replace_text."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        old = str(old)
        new = str(new)

        try:
            full_path = self._resolve_safe_path(path)
        except ValueError as exc:
            message = f"replace_text zablokowane: {exc}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        if not os.path.exists(full_path):
            message = f"Plik nie istnieje: {path}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {"path": path}, tool_call_id)
            return events, result

        with open(full_path, encoding="utf-8") as handle:
            content = handle.read()

        if old not in content:
            output = "Wzorzec nie znaleziony, brak zmian."
            events.append({"type": "tool_output", "content": output})
            events.append({"type": "final_response", "content": "Brak zmian do zastosowania."})
            result = self._make_tool_result(
                tool_name,
                True,
                output,
                {"path": path, "changed": False, "replacements": 0},
                tool_call_id,
            )
            return events, result

        replace_all = False
        replace_count = _coerce_int(count, 1)
        if count is None:
            replace_count = 1
        elif replace_count <= 0:
            replace_all = True

        original_count = content.count(old)
        if replace_all:
            updated = content.replace(old, new)
            replacements = original_count
        else:
            updated = content.replace(old, new, replace_count)
            replacements = min(replace_count, original_count)
        with open(full_path, "w", encoding="utf-8") as handle:
            handle.write(updated)

        output = f"Zaktualizowano: {path}"
        events.append({"type": "tool_output", "content": output})
        events.append({"type": "final_response", "content": "Zmiana zakończona."})
        result = self._make_tool_result(
            tool_name,
            True,
            output,
            {"path": path, "changed": True, "replacements": replacements},
            tool_call_id,
        )
        return events, result

    def _handle_apply_patch(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        patch_text = tool.get("patch") or tool.get("diff") or tool.get("command")
        if not patch_text:
            message = "Brak patch/diff w apply_patch."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result
        if patch_text.lstrip().startswith("*** Begin Patch"):
            message = "Niewspierany format patcha. Użyj unified diff."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        ok, output = self._apply_patch_text(patch_text)
        if output:
            events.append({"type": "tool_output", "content": output})
        if ok:
            events.append({"type": "final_response", "content": "Patch zastosowany."})
        else:
            events.append({"type": "final_response", "content": "Patch nie został zastosowany."})

        result = self._make_tool_result(
            tool_name,
            ok,
            output or "",
            {"paths": self._extract_patch_paths(patch_text)},
            tool_call_id,
        )
        return events, result

    async def _handle_shell(self, tool: dict[str, Any], tool_name: str, tool_call_id: str | None):
        events: list[dict[str, Any]] = []
        command = tool.get("command")
        if not command:
            message = "Brak command w shell tool."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(tool_name, False, message, {}, tool_call_id)
            return events, result

        if not self.allow_shell:
            message = "Wykonywanie shell jest wyłączone w proxy (allow_shell=false)."
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(
                tool_name,
                False,
                message,
                {"command": command},
                tool_call_id,
            )
            return events, result

        pattern = self._matches_blacklist(command)
        if pattern:
            message = f"Polecenie zablokowane przez blacklistę: {pattern}"
            events.append({"type": "final_response", "content": message})
            result = self._make_tool_result(
                tool_name,
                False,
                message,
                {"command": command},
                tool_call_id,
            )
            return events, result

        events.append({"type": "status", "content": f"Wykonywanie: {command}"})
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=self.workspace_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += stderr.decode("utf-8", errors="replace")
        if output.strip():
            self.logger.debug("Shell %s output (%s chars)", command, len(output.strip()))
            events.append({"type": "tool_output", "content": output.strip()})
        events.append({"type": "final_response", "content": f"Exit code: {process.returncode}"})
        result = self._make_tool_result(
            tool_name,
            process.returncode == 0,
            output.strip(),
            {"command": command, "returncode": process.returncode},
            tool_call_id,
        )
        return events, result

    def _prepare_message(self, user_text: str) -> tuple[str, bool, bool]:
        self._last_context_meta = None
        self._observer_meta = None
        observer_included = False
        context_included = False
        snapshot: dict[str, Any] | None = None
        observer_text: str | None = None
        context_text: str | None = None

        if self.observer_enabled:
            snapshot = self._collect_workspace_snapshot()
            if self._should_send_observer(snapshot["signature"]):
                observer_text, meta = self._build_observer_summary(snapshot)
                self._observer_signature = snapshot["signature"]
                self._observer_meta = meta
                observer_included = True

        if self.context_enabled and self.context_mode != "manual":
            if snapshot is None:
                snapshot = self._collect_workspace_snapshot()
            context_text, signature, meta = self._build_context_bundle(snapshot)
            if self._should_send_context(signature):
                self._context_signature = signature
                self._last_context_meta = meta
                context_included = True
            else:
                context_text = None

        if observer_included or context_included:
            parts: list[str] = []
            if observer_text:
                parts.append(observer_text)
            if context_text:
                parts.append(context_text)
            parts.append(f"USER: {user_text}")
            return "\n\n".join(parts), context_included, observer_included

        return user_text, False, False

    def _should_send_context(self, signature: str) -> bool:
        mode = self.context_mode
        if mode == "always":
            return True
        if mode == "once":
            return self._context_signature is None or self.context_id is None
        if mode == "on_change":
            return self._context_signature != signature or self.context_id is None
        return False

    def _should_send_observer(self, signature: str) -> bool:
        mode = self.observer_mode
        if mode in ("manual", "off", "disabled", "false"):
            return False
        if mode == "always":
            return True
        return self._observer_signature != signature

    def _build_observer_summary(self, snapshot: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        lines = [
            "[AZ_OBSERVER v1]",
            "role: read-only workspace observer",
            "policy: no tool execution, no file mutation",
            f"project: {self.project_name}",
            f"context_hash: {snapshot['signature']}",
            f"files: {snapshot['file_count']} total, {snapshot['total_bytes']} bytes",
        ]

        tree_lines = snapshot.get("tree_lines") or []
        if tree_lines:
            lines.append("workspace_tree_sample:")
            for line in tree_lines[:8]:
                lines.append(f"- {line}")
            if len(tree_lines) > 8 or snapshot.get("tree_truncated"):
                lines.append("- ... [truncated]")

        previews = [path for path, _ in snapshot.get("previews", [])]
        if previews:
            preview_list = ", ".join(previews[:4])
            suffix = ", ..." if len(previews) > 4 else ""
            lines.append(f"preview_files: {preview_list}{suffix}")

        lines.append("[/AZ_OBSERVER]")
        meta = {
            "signature": snapshot["signature"],
            "file_count": snapshot["file_count"],
            "total_bytes": snapshot["total_bytes"],
            "preview_files": previews,
        }
        return "\n".join(lines), meta

    def _build_context_bundle(
        self,
        snapshot: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        if snapshot is None:
            snapshot = self._collect_workspace_snapshot()
        context_lines: list[str] = []
        context_lines.append("[AZ_CONTEXT v1]")
        context_lines.append(
            "role: Local proxy. You must request files via tool calls; do not assume."
        )
        context_lines.append("policy: use relative paths inside workspace_root only.")
        context_lines.append(f"project: {self.project_name}")
        if self.agent_profile_name:
            context_lines.append(f"agent_profile: {self.agent_profile_name}")
        if self.agent_profile_prompt:
            context_lines.append(f"agent_profile_prompt: {self.agent_profile_prompt}")

        if self.context_include_system:
            context_lines.append(f"time_utc: {datetime.utcnow().isoformat()}Z")
            context_lines.append(f"workspace_root: {self.workspace_root}")
            context_lines.append(f"cwd: {os.getcwd()}")
            context_lines.append(f"security_mode: {self.security_mode}")
            context_lines.append("path_policy: use relative paths inside workspace_root")
            context_lines.append(f"ignore_dirs: {', '.join(self.context_ignore_dirs)}")

        context_lines.append(f"context_hash: {snapshot['signature']}")
        context_lines.append(
            f"files: {snapshot['file_count']} total, {snapshot['total_bytes']} bytes"
        )

        if self.context_include_tools:
            context_lines.append("tools:")
            for tool_line in self._describe_tools():
                context_lines.append(f"- {tool_line}")

        if self.context_include_tree and snapshot["tree_lines"]:
            context_lines.append("workspace_tree:")
            context_lines.extend(f"- {line}" for line in snapshot["tree_lines"])
            if snapshot["tree_truncated"]:
                context_lines.append("- ... [truncated]")

        if self.context_include_git:
            git_lines = self._get_git_status()
            if git_lines:
                context_lines.append("git_status:")
                context_lines.extend(f"- {line}" for line in git_lines)

        if self.context_include_previews and snapshot["previews"]:
            context_lines.append("file_previews:")
            for path, content in snapshot["previews"]:
                context_lines.append(f"--- {path} ---")
                context_lines.append(content)

        context_lines.append("[/AZ_CONTEXT]")
        context_text = "\n".join(context_lines)
        context_text = self._truncate_context(context_text)

        meta = {
            "signature": snapshot["signature"],
            "file_count": snapshot["file_count"],
            "total_bytes": snapshot["total_bytes"],
            "tree_truncated": snapshot["tree_truncated"],
            "preview_files": [path for path, _ in snapshot["previews"]],
            "context_bytes": len(context_text),
            "project": self.project_name,
            "agent_profile": self.agent_profile_name,
        }
        return context_text, snapshot["signature"], meta

    def _format_observer_status(self) -> str:
        meta = self._observer_meta or {}
        if not meta:
            return ""
        file_count = meta.get("file_count", 0)
        total_bytes = meta.get("total_bytes", 0)
        previews = meta.get("preview_files") or []
        preview_text = ", ".join(previews[:4]) if previews else "none"
        if len(previews) > 4:
            preview_text += ", ..."
        hash_short = str(meta.get("signature", ""))[:8]
        return (
            f"Observer summary ready: files={file_count}, workspace={total_bytes}B, "
            f"previews=[{preview_text}], hash={hash_short}"
        )

    def _format_context_status(self) -> str:
        meta = self._last_context_meta or {}
        if not meta:
            return ""
        file_count = meta.get("file_count", 0)
        total_bytes = meta.get("total_bytes", 0)
        context_bytes = meta.get("context_bytes", 0)
        previews = meta.get("preview_files") or []
        preview_text = ", ".join(previews[:4]) if previews else "none"
        if len(previews) > 4:
            preview_text += ", ..."
        hash_short = str(meta.get("signature", ""))[:8]
        project = meta.get("project", "default")
        profile = meta.get("agent_profile", "default")
        return (
            f"Context ready ({project}/{profile}): files={file_count}, "
            f"workspace={total_bytes}B, context={context_bytes}B, "
            f"previews=[{preview_text}], hash={hash_short}"
        )

    def _collect_workspace_snapshot(self) -> dict[str, Any]:
        tree_lines: list[str] = []
        signature_parts: list[str] = []
        file_records: list[str] = []
        total_files = 0
        total_bytes = 0
        tree_truncated = False
        ignore = set(self.context_ignore_dirs)

        for dirpath, dirnames, filenames in os.walk(self.workspace_root):
            rel_dir = os.path.relpath(dirpath, self.workspace_root)
            depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
            dirnames[:] = [d for d in dirnames if d not in ignore]
            if depth >= self.context_max_depth:
                dirnames[:] = []

            for name in sorted(filenames):
                if total_files >= self.context_max_files:
                    tree_truncated = True
                    break
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, self.workspace_root)
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue
                total_files += 1
                total_bytes += stat.st_size
                file_records.append(rel_path)
                signature_parts.append(f"{rel_path}:{int(stat.st_mtime)}:{stat.st_size}")
                if self.context_include_tree:
                    tree_lines.append(f"{rel_path} ({stat.st_size}B)")
            if tree_truncated:
                break

        signature_raw = "\n".join(signature_parts).encode("utf-8")
        signature = hashlib.sha256(signature_raw).hexdigest() if signature_raw else "empty"

        previews: list[tuple] = []
        if self.context_include_previews:
            preview_files = self._select_preview_files(file_records)
            for rel_path in preview_files:
                preview = self._read_preview(rel_path)
                if preview is not None:
                    previews.append((rel_path, preview))

        return {
            "tree_lines": tree_lines,
            "tree_truncated": tree_truncated,
            "signature": signature,
            "previews": previews,
            "file_count": total_files,
            "total_bytes": total_bytes,
        }

    # SECURITY: Files that should never be included in preview (may contain secrets)
    SENSITIVE_FILES = frozenset(
        {
            "config.yaml",
            "config.yml",
            "config.json",
            ".env",
            ".env.local",
            ".env.production",
            "secrets.yaml",
            "secrets.yml",
            "secrets.json",
            "credentials.json",
            "credentials.yaml",
            ".npmrc",
            ".pypirc",
            ".netrc",
            "id_rsa",
            "id_ed25519",
            "*.pem",
            "*.key",
        }
    )

    def _select_preview_files(self, file_records: list[str]) -> list[str]:
        if isinstance(self.context_preview_files, list) and self.context_preview_files:
            candidates = self.context_preview_files
        else:
            candidates = [
                "README.md",
                "README.txt",
                "README",
                "main.py",
                "backend.py",
                "config.example.yaml",
                "requirements.txt",
            ]
        chosen: list[str] = []
        for name in candidates:
            # SECURITY: Skip sensitive files
            if self._is_sensitive_file(name):
                continue
            if name in file_records or os.path.exists(os.path.join(self.workspace_root, name)):
                chosen.append(name)
        return chosen

    def _read_preview(self, rel_path: str) -> str | None:
        try:
            full_path = self._resolve_safe_path(rel_path)
        except ValueError:
            return None
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            return None
        try:
            with open(full_path, encoding="utf-8", errors="replace") as handle:
                content = handle.read(self.context_max_preview_bytes + 1)
        except OSError:
            return None
        content = self._redact_preview_content(content)
        if len(content) > self.context_max_preview_bytes:
            content = content[: self.context_max_preview_bytes] + "\n... [truncated]"
        return content

    def _redact_preview_content(self, content: str) -> str:
        if not content:
            return content
        redacted = content
        for key in self.context_redact_keys:
            if not key:
                continue
            yaml_pattern = re.compile(rf"(?im)^(\s*{re.escape(key)}\s*:\s*)(.+?)(\s*)$")
            redacted = yaml_pattern.sub(r"\1***REDACTED***\3", redacted)
            json_pattern = re.compile(rf'(?im)^(\s*"{re.escape(key)}"\s*:\s*)(".*?"|\S+)(\s*,?)$')
            redacted = json_pattern.sub(r'\1"***REDACTED***"\3', redacted)
        for pattern in self.context_redact_patterns:
            try:
                redacted = re.sub(pattern, "***REDACTED***", redacted, flags=re.IGNORECASE)
            except re.error:
                continue
        return redacted

    def _is_sensitive_file(self, rel_path: str) -> bool:
        """Return True if the given path matches a sensitive pattern."""
        if not rel_path:
            return False
        candidate = rel_path.replace(os.sep, "/")
        base = os.path.basename(rel_path)
        for pattern in self.SENSITIVE_FILES:
            if not pattern:
                continue
            if fnmatch.fnmatch(candidate, pattern) or fnmatch.fnmatch(base, pattern):
                return True
        return False

    def _resolve_agent_profile(self, config: dict[str, Any]) -> tuple[str, str]:
        env_profile = os.environ.get("AGENTZERO_AGENT_PROFILE")
        selected = env_profile or config.get("agent_profile")
        profiles = config.get("agent_profiles", {})

        if isinstance(selected, dict):
            name = selected.get("name") or "custom"
            prompt = selected.get("prompt") or selected.get("instructions") or ""
            return name, prompt

        name = selected if isinstance(selected, str) else None

        if isinstance(profiles, dict) and profiles:
            if name and name in profiles:
                profile_cfg = profiles[name]
            else:
                name = next(iter(profiles))
                profile_cfg = profiles[name]
            if isinstance(profile_cfg, dict):
                prompt = profile_cfg.get("prompt") or profile_cfg.get("instructions") or ""
            else:
                prompt = str(profile_cfg)
            return name or "default", prompt

        if name:
            return name, ""
        return "default", ""

    def _describe_tools(self) -> list[str]:
        """Describe available tools with approval status tags."""
        readonly = {"read_file", "list_files", "search_text"}

        def tag(name: str) -> str:
            if self.security_mode == "god_mode":
                return "[auto]"
            if self.security_mode == "paranoid":
                return "[approval]"
            # balanced mode
            return "[auto]" if name in readonly else "[approval]"

        tools = [
            f"read_file(path, start_line?, end_line?, max_bytes?) {tag('read_file')}",
            f"list_files(path='.', max_depth?, max_files?) {tag('list_files')}",
            f"search_text(query, path='.', max_matches?, case_sensitive?) {tag('search_text')}",
            f"write_file(path, content) {tag('write_file')}",
            f"replace_text(path, old, new, count?) {tag('replace_text')}",
            f"apply_patch(patch) {tag('apply_patch')}",
        ]
        if self.allow_shell:
            tools.append(f"shell(command) {tag('shell')}")
        else:
            tools.append("shell(command) [disabled]")
        return tools

    def _get_git_status(self) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return [f"git error: {exc}"]
        if result.returncode != 0:
            return []

        status_lines: list[str] = []
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
        )
        branch_name = branch.stdout.strip() if branch.returncode == 0 else "unknown"
        status_lines.append(f"branch: {branch_name}")

        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
        )
        if status.returncode == 0:
            lines = [line for line in status.stdout.splitlines() if line.strip()]
            if not lines:
                status_lines.append("clean")
            else:
                status_lines.extend(lines[:50])
                if len(lines) > 50:
                    status_lines.append("... [truncated]")
        return status_lines

    def _truncate_context(self, context_text: str) -> str:
        if len(context_text) <= self.context_max_bytes:
            return context_text
        truncated = context_text[: self.context_max_bytes]
        if "[/AZ_CONTEXT]" not in truncated:
            truncated = truncated.rsplit("\n", 1)[0]
            truncated += "\n... [truncated]\n[/AZ_CONTEXT]"
        return truncated

    async def _run_request(self, payload: dict[str, Any], allow_stream: bool):
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        start = time.monotonic()

        def push(item: Any):
            loop.call_soon_threadsafe(queue.put_nowait, item)

        def worker():
            try:
                if allow_stream:
                    for event in self._stream_message(payload):
                        push(event)
                else:
                    data = self._post_message(payload)
                    for event in self._extract_events(data):
                        push(event)
            except Exception as exc:
                push({"type": "final_response", "content": f"❌ Błąd połączenia: {exc}"})
            finally:
                push(None)

        threading.Thread(target=worker, daemon=True).start()
        yield {
            "type": "status",
            "content": f"Zapytanie wysłane (stream={'on' if allow_stream else 'off'}).",
        }

        while True:
            try:
                if self.keepalive_seconds and self.keepalive_seconds > 0:
                    item = await asyncio.wait_for(queue.get(), timeout=self.keepalive_seconds)
                else:
                    item = await queue.get()
            except asyncio.TimeoutError:
                elapsed = int(time.monotonic() - start)
                yield {
                    "type": "status",
                    "content": (
                        f"⏳ Oczekiwanie na odpowiedź... {elapsed}s " "(połączenie aktywne)"
                    ),
                }
                if self.max_wait_seconds and self.max_wait_seconds > 0:
                    if elapsed >= self.max_wait_seconds:
                        yield {
                            "type": "final_response",
                            "content": "⏱ Limit oczekiwania przekroczony.",
                        }
                        return
                continue

            if item is None:
                break
            yield item

    def _stream_message(self, payload: dict[str, Any]):
        if self.stream_enabled:
            payload = dict(payload)
            payload.setdefault("stream", True)
        request = self._build_request(payload, stream=True)
        timeout = None if self.timeout_seconds <= 0 else self.timeout_seconds
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            mode = self._select_stream_mode(content_type)
            yield {"type": "status", "content": f"Połączono z serwerem (stream={mode})."}

            if mode == "sse":
                for event in self._iter_sse(response):
                    yield event
                return

            if mode == "jsonl":
                for event in self._iter_jsonl(response):
                    yield event
                return

            raw = response.read().decode("utf-8", errors="replace")
            if not raw:
                return
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"response": raw}
            for event in self._extract_events(data):
                yield event

    def _iter_sse(self, response):
        event_type = None
        data_lines: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                if not data_lines:
                    event_type = None
                    continue
                data = "\n".join(data_lines)
                data_lines = []
                if data.strip() in ("[DONE]", "[FINISH]"):
                    break
                parsed = self._maybe_parse_json(data)
                if parsed is not None:
                    # Extract context_id from SSE response
                    if isinstance(parsed, dict) and "context_id" in parsed and parsed["context_id"]:
                        self.context_id = parsed["context_id"]
                    yield from self._normalize_response(parsed)
                else:
                    yield {
                        "type": event_type or "final_response",
                        "content": data,
                    }
                event_type = None
                continue

            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
                continue

    def _iter_jsonl(self, response):
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            parsed = self._maybe_parse_json(line)
            if parsed is not None:
                # Extract context_id from stream response
                if isinstance(parsed, dict) and "context_id" in parsed and parsed["context_id"]:
                    self.context_id = parsed["context_id"]
                yield from self._normalize_response(parsed)
            else:
                yield {"type": "final_response", "content": line}

    def _select_stream_mode(self, content_type: str) -> str:
        mode = (self.stream_mode or "auto").lower()
        if mode in ("sse", "jsonl"):
            return mode
        ct = content_type.lower()
        if "text/event-stream" in ct:
            return "sse"
        if "ndjson" in ct or "jsonl" in ct or "application/x-ndjson" in ct:
            return "jsonl"
        return "none"

    async def _post_tool_result(self, result: dict[str, Any]):
        if not self.api_url:
            return
        if not self.context_id:
            yield {"type": "status", "content": "Brak context_id - pomijam wysyłkę wyniku."}
            return

        payload = {
            "message": json.dumps({"tool_result": result}, ensure_ascii=False),
            "lifetime_hours": self.lifetime_hours,
            "context_id": self.context_id,
        }
        yield {"type": "status", "content": "Wysyłam wynik narzędzia do agenta..."}
        async for event in self._run_request(payload, allow_stream=self.stream_enabled):
            yield event

    def _make_tool_result(
        self,
        tool_name: str,
        ok: bool,
        output: str,
        details: dict[str, Any] | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        result = {
            "tool_name": tool_name,
            "ok": ok,
            "output": output,
            "details": details or {},
        }
        if tool_call_id:
            result["tool_call_id"] = tool_call_id
        return result

    def _resolve_api_url(self, connection: dict[str, Any]) -> str | None:
        env_url = os.environ.get("AGENTZERO_API_URL")
        if env_url:
            return env_url
        if connection.get("api_url"):
            return connection["api_url"]
        host = connection.get("host")
        port = connection.get("port")
        path = connection.get("path", "/api_message")
        if not host or not port:
            return None
        return f"http://{host}:{port}{path}"

    def _build_request(self, payload: dict[str, Any], stream: bool):
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        if stream:
            headers["Accept"] = "text/event-stream"
        return urllib.request.Request(self.api_url, data=body, headers=headers, method="POST")

    def _post_message(self, payload: dict[str, Any]):
        request = self._build_request(payload, stream=False)
        timeout = None if self.timeout_seconds <= 0 else self.timeout_seconds
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"response": raw}

    def _extract_events(self, data: Any) -> Iterable[dict[str, Any]]:
        if isinstance(data, dict):
            self._maybe_set_context_id(data)
            response = data.get("response", data.get("message", data))
        else:
            response = data
        return self._normalize_response(response)

    def _normalize_response(self, response: Any) -> list[dict[str, Any]]:
        if response is None:
            return []

        if isinstance(response, str):
            parsed = self._maybe_parse_json(response)
            if parsed is not None:
                return self._normalize_response(parsed)
            return [{"type": "final_response", "content": response}]

        if isinstance(response, list):
            for item in response:
                self._maybe_set_context_id(item)
            events: list[dict[str, Any]] = []
            for item in response:
                events.extend(self._normalize_response(item))
            return events

        if isinstance(response, dict):
            self._maybe_set_context_id(response)
            if "choices" in response and isinstance(response["choices"], list):
                events: list[dict[str, Any]] = []
                for choice in response["choices"]:
                    if not isinstance(choice, dict):
                        continue
                    if "delta" in choice and isinstance(choice["delta"], dict):
                        content = choice["delta"].get("content")
                        if content:
                            events.append({"type": "thinking", "content": content})
                    elif "message" in choice and isinstance(choice["message"], dict):
                        content = choice["message"].get("content")
                        if content:
                            events.append({"type": "final_response", "content": content})
                if events:
                    return events
            if "tool_calls" in response:
                events = []
                if response.get("content"):
                    events.extend(
                        self._normalize_response(
                            {"type": "final_response", "content": response.get("content")}
                        )
                    )
                events.extend(self._normalize_tool_calls(response.get("tool_calls")))
                return events
            if "tool_call" in response:
                return self._normalize_tool_calls([response.get("tool_call")])
            if response.get("type") == "tool_use":
                return [self._normalize_tool_event(self._coerce_tool_call(response))]
            if "delta" in response and isinstance(response["delta"], dict):
                content = response["delta"].get("content")
                if content:
                    return [{"type": "thinking", "content": content}]
            if "events" in response:
                return self._normalize_response(response["events"])
            if "tool_request" in response:
                return [self._normalize_tool_event(response["tool_request"])]

            event_type = response.get("type")
            if event_type:
                if event_type in ("tool_request", "tool_call", "tool"):
                    return [self._normalize_tool_event(response)]
                if event_type == "text":
                    return [
                        {
                            "type": "final_response",
                            "content": response.get("text") or response.get("content") or "",
                        }
                    ]
                if event_type in ("final_response", "message", "answer"):
                    content = (
                        response.get("content")
                        or response.get("message")
                        or response.get("text")
                        or ""
                    )
                    return [{"type": "final_response", "content": content}]
                if "content" in response:
                    return [{"type": event_type, "content": response.get("content")}]
                return [response]

            if "response" in response or "message" in response:
                return self._normalize_response(response.get("response") or response.get("message"))

            return [
                {
                    "type": "final_response",
                    "content": json.dumps(response, ensure_ascii=False),
                }
            ]

        return [{"type": "final_response", "content": str(response)}]

    def _normalize_tool_event(self, event: dict[str, Any]) -> dict[str, Any]:
        tool_name = event.get("tool_name") or event.get("name") or event.get("tool") or "tool"
        reason = event.get("reason") or "Brak uzasadnienia."
        command = event.get("command") or event.get("summary")
        if not command:
            command = self._summarize_tool(tool_name, event)
        return {
            "type": "tool_request",
            "tool_name": tool_name,
            "command": command,
            "reason": reason,
            "payload": event,
        }

    def _normalize_tool_calls(self, calls: Any) -> list[dict[str, Any]]:
        if not calls:
            return []
        if not isinstance(calls, list):
            calls = [calls]
        events: list[dict[str, Any]] = []
        for call in calls:
            payload = self._coerce_tool_call(call)
            events.append(self._normalize_tool_event(payload))
        return events

    def _coerce_tool_call(self, call: Any) -> dict[str, Any]:
        if not isinstance(call, dict):
            return {"tool_name": "tool", "command": str(call)}

        tool_name = call.get("tool_name") or call.get("name")
        tool_call_id = call.get("tool_call_id") or call.get("id")
        args = None

        if isinstance(call.get("function"), dict):
            tool_name = tool_name or call["function"].get("name")
            args = call["function"].get("arguments")

        if args is None:
            args = call.get("arguments") or call.get("input")

        payload = self._parse_tool_arguments(args)
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            payload = {"arguments": payload}

        if tool_name:
            payload.setdefault("tool_name", tool_name)
        if tool_call_id:
            payload.setdefault("tool_call_id", tool_call_id)
        if call.get("reason"):
            payload.setdefault("reason", call.get("reason"))
        if call.get("command"):
            payload.setdefault("command", call.get("command"))

        return payload

    def _parse_tool_arguments(self, args: Any) -> Any:
        if args is None:
            return None
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            parsed = self._maybe_parse_json(args)
            return parsed if parsed is not None else args
        return args

    def _summarize_tool(self, tool_name: str, payload: dict[str, Any]) -> str:
        if tool_name in ("write_file", "file_write"):
            path = payload.get("path") or payload.get("file") or payload.get("target")
            size = len(payload.get("content") or payload.get("text") or "")
            if path:
                return f"write_file {path} ({size} chars)"
            return f"write_file ({size} chars)"
        if tool_name in ("replace_text", "replace"):
            path = payload.get("path") or payload.get("file") or payload.get("target")
            return f"replace_text {path}" if path else "replace_text"
        if tool_name in ("apply_patch", "patch"):
            size = len(payload.get("patch") or payload.get("diff") or "")
            return f"apply_patch ({size} chars)"
        if tool_name in ("terminal", "shell", "command"):
            return payload.get("command") or "shell"
        return f"{tool_name}"

    def _coerce_tool_event(self, tool_event: Any) -> dict[str, Any]:
        if isinstance(tool_event, dict):
            if tool_event.get("payload") and tool_event.get("tool_name"):
                payload = tool_event.get("payload")
                if isinstance(payload, dict):
                    payload = payload.copy()
                    payload.setdefault("tool_name", tool_event.get("tool_name"))
                    payload.setdefault("command", tool_event.get("command"))
                    payload.setdefault("reason", tool_event.get("reason"))
                    return payload
            return tool_event
        if isinstance(tool_event, str):
            return {"tool_name": "terminal", "command": tool_event}
        return {"tool_name": "tool", "command": str(tool_event)}

    def _matches_blacklist(self, command: str) -> str | None:
        if not command:
            return None
        lowered = command.lower()
        for pattern in self.blacklist_patterns:
            if pattern.lower() in lowered:
                return pattern
        return None

    def _resolve_safe_path(self, path: str) -> str:
        if os.path.isabs(path):
            raise ValueError("Ścieżka absolutna jest zablokowana.")
        normalized = os.path.normpath(path)
        if normalized.startswith("..") or normalized == "..":
            raise ValueError("Ścieżka wychodzi poza workspace.")
        workspace_abs = os.path.abspath(self.workspace_root)
        full_path = os.path.abspath(os.path.join(workspace_abs, normalized))
        workspace_real = os.path.realpath(workspace_abs)
        full_real = os.path.realpath(full_path)
        if os.path.commonpath([workspace_real, full_real]) != workspace_real:
            raise ValueError("Ścieżka poza workspace.")
        return full_real

    def _apply_patch_text(self, patch_text: str):
        patch_cmd = shutil.which("patch")
        if not patch_cmd:
            return False, "Brak narzędzia 'patch' w systemie."

        paths = self._extract_patch_paths(patch_text)
        for path in paths:
            try:
                self._resolve_safe_path(path)
            except ValueError as exc:
                return False, f"Patch zablokowany: {exc}"

        strip_level = 1 if self._uses_git_prefix(patch_text) else 0

        handle = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        try:
            handle.write(patch_text)
            handle.close()
            result = subprocess.run(
                [patch_cmd, f"-p{strip_level}", "--batch", "--forward", "-i", handle.name],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
            )
        finally:
            try:
                os.unlink(handle.name)
            except OSError:
                pass

        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        return result.returncode == 0, output

    def _extract_patch_paths(self, patch_text: str) -> list[str]:
        paths: list[str] = []
        for line in patch_text.splitlines():
            if line.startswith(("--- ", "+++ ")):
                path = line.split(" ", 1)[1].strip()
                if path == "/dev/null":
                    continue
                if not path:
                    continue
                if path.startswith(("a/", "b/")):
                    path = path[2:]
                paths.append(path)
            elif line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    for raw in (parts[2], parts[3]):
                        if raw.startswith(("a/", "b/")):
                            raw = raw[2:]
                        if not raw:
                            continue
                        paths.append(raw)
        return list(dict.fromkeys(paths))

    def _uses_git_prefix(self, patch_text: str) -> bool:
        for line in patch_text.splitlines():
            if line.startswith(("diff --git a/", "--- a/", "+++ b/")):
                return True
        return False

    def _maybe_parse_json(self, text: str) -> Any | None:
        stripped = text.strip()
        if not stripped or stripped[0] not in "{[":
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None

    def _maybe_set_context_id(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        for key in ("context_id", "contextId", "conversation_id", "conversationId"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                self.context_id = value
                return
