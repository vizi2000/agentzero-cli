"""
Real tool execution for Agent Zero CLI.

Executes shell commands, file operations with proper security checks.
"""

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: str
    error: str = ""
    return_code: int = 0


# Dangerous patterns that should never be executed
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    ":(){ :|:& };:",  # fork bomb
    "mkfs.",
    "dd if=/dev/",
    "> /dev/sda",
    "chmod -R 777 /",
    "wget.*|.*sh",
    "curl.*|.*sh",
]

# Commands that modify system state (require confirmation in balanced mode)
WRITE_COMMANDS = [
    "rm", "rmdir", "mv", "cp", "mkdir", "touch",
    "chmod", "chown", "ln",
    "git push", "git commit", "git reset",
    "pip install", "npm install", "apt install",
]

# Safe read-only commands (auto-approve in balanced mode)
READONLY_COMMANDS = [
    "ls", "cat", "head", "tail", "less", "more",
    "grep", "find", "which", "whereis", "file",
    "wc", "diff", "pwd", "echo", "date", "whoami",
    "git status", "git log", "git diff", "git branch",
    "python --version", "node --version", "pip list",
]


def is_blocked(command: str) -> tuple[bool, str]:
    """Check if command matches any blocked pattern."""
    cmd_lower = command.lower().strip()
    
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            return True, f"Blocked dangerous pattern: {pattern}"
    
    return False, ""


def is_readonly(command: str) -> bool:
    """Check if command is read-only (safe)."""
    cmd_lower = command.lower().strip()
    
    for safe_cmd in READONLY_COMMANDS:
        if cmd_lower.startswith(safe_cmd):
            return True
    
    return False


def is_write_operation(command: str) -> bool:
    """Check if command modifies state."""
    cmd_lower = command.lower().strip()
    
    for write_cmd in WRITE_COMMANDS:
        if cmd_lower.startswith(write_cmd):
            return True
    
    # Check for redirections
    if ">" in command or ">>" in command:
        return True
    
    return False


async def execute_shell(
    command: str,
    cwd: str | None = None,
    timeout: int = 60
) -> ToolResult:
    """
    Execute a shell command asynchronously.
    
    Args:
        command: Shell command to execute
        cwd: Working directory (default: current)
        timeout: Timeout in seconds
    
    Returns:
        ToolResult with output, error, and return code
    """
    # Security check
    blocked, reason = is_blocked(command)
    if blocked:
        return ToolResult(
            success=False,
            output="",
            error=f"Command blocked: {reason}",
            return_code=-1
        )
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env={**os.environ, "TERM": "dumb"}  # Disable color codes
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s",
                return_code=-1
            )
        
        output = stdout.decode("utf-8", errors="replace").strip()
        error = stderr.decode("utf-8", errors="replace").strip()
        
        # Truncate very long output
        max_output = 10000
        if len(output) > max_output:
            output = output[:max_output] + f"\n... (truncated, {len(output)} total chars)"
        
        return ToolResult(
            success=process.returncode == 0,
            output=output,
            error=error,
            return_code=process.returncode or 0
        )
        
    except Exception as e:
        return ToolResult(
            success=False,
            output="",
            error=f"Execution error: {str(e)}",
            return_code=-1
        )


async def read_file(path: str, max_lines: int = 500) -> ToolResult:
    """Read file contents."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return ToolResult(False, "", f"File not found: {path}")
        if not p.is_file():
            return ToolResult(False, "", f"Not a file: {path}")
        
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines])
            content += f"\n... ({len(lines) - max_lines} more lines)"
        
        return ToolResult(True, content)
        
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(False, "", f"Read error: {str(e)}")


async def write_file(path: str, content: str) -> ToolResult:
    """Write content to file."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Written {len(content)} bytes to {path}")
        
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(False, "", f"Write error: {str(e)}")


async def list_files(path: str = ".", max_depth: int = 2) -> ToolResult:
    """List files in directory."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return ToolResult(False, "", f"Directory not found: {path}")
        if not p.is_dir():
            return ToolResult(False, "", f"Not a directory: {path}")
        
        files = []
        for item in sorted(p.iterdir()):
            prefix = "d " if item.is_dir() else "f "
            files.append(f"{prefix}{item.name}")
        
        return ToolResult(True, "\n".join(files))
        
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(False, "", f"List error: {str(e)}")


async def execute_tool(
    tool_name: str,
    command: str,
    cwd: str | None = None
) -> AsyncGenerator[dict, None]:
    """
    Execute a tool and yield status updates.
    
    Args:
        tool_name: Type of tool (shell, read_file, write_file, etc.)
        command: Command or arguments
        cwd: Working directory
    
    Yields:
        Dict with type and content for each status update
    """
    yield {"type": "status", "content": f"Executing: {tool_name}"}
    
    if tool_name in ("shell", "terminal", "command", "bash"):
        result = await execute_shell(command, cwd)
        
    elif tool_name == "read_file":
        result = await read_file(command)
        
    elif tool_name == "write_file":
        # Expect command as "path|||content"
        if "|||" in command:
            path, content = command.split("|||", 1)
            result = await write_file(path.strip(), content)
        else:
            result = ToolResult(False, "", "Invalid write_file format")
            
    elif tool_name in ("list_files", "ls", "tree"):
        result = await list_files(command or ".")
        
    else:
        # Default to shell execution
        result = await execute_shell(command, cwd)
    
    if result.success:
        yield {"type": "tool_output", "content": result.output or "(no output)"}
    else:
        error_msg = result.error or f"Command failed with code {result.return_code}"
        yield {"type": "tool_output", "content": f"[ERROR] {error_msg}"}
        if result.output:
            yield {"type": "tool_output", "content": result.output}
    
    yield {"type": "status", "content": "Execution complete"}
