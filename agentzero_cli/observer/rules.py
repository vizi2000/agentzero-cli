"""Rule-based routing for known tool patterns."""

from typing import Any

# Same as cli/approval.py READONLY_TOOLS
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

# Write tools that always need approval
WRITE_TOOLS = frozenset(
    {
        "write_file",
        "file_write",
        "replace_text",
        "replace",
        "apply_patch",
        "patch",
    }
)

# Shell aliases
SHELL_TOOLS = frozenset({"terminal", "shell", "command"})


def route_by_rules(
    tool_name: str,
    params: dict[str, Any],
    security_mode: str,
    whitelist: list[str],
    blacklist: list[str],
) -> str | None:
    """
    Return routing decision if rules match, None if LLM fallback needed.

    Returns:
        "auto" - auto-approve and execute
        "approve" - show approval dialog
        "block" - reject immediately
        None - no rule matched, use LLM fallback
    """
    name = tool_name.lower()

    # god_mode = always auto
    if security_mode == "god_mode":
        return "auto"

    # paranoid = always ask
    if security_mode == "paranoid":
        return "approve"

    # balanced mode logic
    if name in READONLY_TOOLS:
        return "auto"

    if name in WRITE_TOOLS:
        return "approve"

    if name in SHELL_TOOLS:
        command = (params.get("command") or "").strip().lower()

        # Check blacklist first
        for pattern in blacklist:
            if pattern.lower() in command:
                return "block"

        # Check whitelist
        for entry in whitelist:
            if command.startswith(str(entry).lower()):
                return "auto"

        return "approve"

    # Unknown tool - needs LLM fallback
    return None
