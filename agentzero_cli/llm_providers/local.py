"""
Local Deterministic Backend for AgentZeroCLI

Rule-based responses without any LLM - works fully offline.
Useful for testing, demos, or when no API is available.
"""

import re
from dataclasses import dataclass
from typing import AsyncGenerator, Optional


@dataclass
class AgentEvent:
    """Event yielded during agent interaction."""
    type: str
    content: str
    tool_call: Optional[dict] = None


# Patterns and their tool responses
COMMAND_PATTERNS = [
    # File listing
    (r"(list|show|what).*(files?|directory|folder|content)", "shell", "ls -la", "List directory contents"),
    (r"(ls|dir)\b", "shell", "ls -la", "List directory contents"),
    
    # File reading
    (r"(read|show|cat|display|open).*(file|content).+?['\"]?(\S+\.(py|txt|md|json|yaml|yml|js|ts|html|css))['\"]?", "read_file", r"\3", "Read file contents"),
    (r"(read|cat)\s+(\S+)", "shell", r"cat \2", "Read file"),
    
    # Git operations
    (r"(git\s+)?status", "shell", "git status", "Check git status"),
    (r"(git\s+)?log", "shell", "git log --oneline -10", "Show recent commits"),
    (r"(git\s+)?diff", "shell", "git diff", "Show uncommitted changes"),
    (r"(git\s+)?branch", "shell", "git branch -a", "List branches"),
    
    # Project info
    (r"(what|which).*(python|node|npm|version)", "shell", "python --version && node --version 2>/dev/null || echo 'node not found'", "Check versions"),
    (r"(project|folder).*(structure|tree)", "shell", "find . -type f -name '*.py' | head -20", "Show project structure"),
    
    # Search
    (r"(find|search|grep|look for).+?['\"](.+?)['\"]", "shell", r"grep -rn '\2' --include='*.py' . | head -20", "Search in code"),
    (r"(find|search).*(function|class|def)\s+(\w+)", "shell", r"grep -rn 'def \3\|class \3' --include='*.py' .", "Find definition"),
    
    # System info
    (r"(pwd|where|current).*(directory|folder|am i)", "shell", "pwd", "Show current directory"),
    (r"(who|user).*am i", "shell", "whoami", "Show current user"),
    (r"(disk|space|storage)", "shell", "df -h .", "Check disk space"),
    
    # Dependencies
    (r"(pip|requirements|dependencies|packages)", "shell", "pip list 2>/dev/null | head -20 || cat requirements.txt 2>/dev/null", "List dependencies"),
    
    # Tests
    (r"(run|execute).*(test|pytest)", "shell", "python -m pytest -v 2>&1 | head -50", "Run tests"),
]

# Informational responses (no tool needed)
INFO_PATTERNS = [
    (r"(hello|hi|hey|cześć|siema)\b", "Hello! I'm Agent Zero CLI in local mode. I can help you explore files, run git commands, and analyze your project. What would you like to do?"),
    (r"(help|what can you|how to)", "I can help you with:\n- List files: 'show files', 'ls'\n- Read files: 'read file.py'\n- Git: 'git status', 'git log', 'git diff'\n- Search: 'find \"pattern\"'\n- Tests: 'run tests'\n\nNote: I'm in LOCAL mode (no LLM). For smarter responses, set OPENROUTER_API_KEY or AGENTZERO_API_URL."),
    (r"(thanks|thank you|dzięki)", "You're welcome! Anything else?"),
    (r"(bye|exit|quit)", "Goodbye! Use Ctrl+C or F10 to exit the application."),
]

# Risk analysis templates
RISK_TEMPLATES = {
    "rm": "HIGH RISK: Deletes files permanently. Ensure you have backups.",
    "sudo": "HIGH RISK: Runs with elevated privileges. Verify the command carefully.",
    "chmod": "MEDIUM RISK: Changes file permissions. May affect security.",
    "mv": "MEDIUM RISK: Moves/renames files. Original location will be empty.",
    "cp": "LOW RISK: Copies files. May overwrite destination.",
    "git push": "MEDIUM RISK: Pushes commits to remote. Cannot easily undo.",
    "git reset": "HIGH RISK: May lose uncommitted changes.",
    "pip install": "MEDIUM RISK: Installs packages. May affect environment.",
    "default": "LOW RISK: Read-only operation or safe command."
}


class LocalBackend:
    """
    Deterministic local backend - no LLM required.
    Uses pattern matching to understand intent and suggest tools.
    """
    
    def __init__(self):
        self.history: list[str] = []
    
    async def send_prompt(self, user_text: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Process user input with pattern matching.
        """
        self.history.append(user_text)
        text_lower = user_text.lower().strip()
        
        yield AgentEvent(type="status", content="[LOCAL] Processing with pattern matching...")
        
        # Check for informational patterns first
        for pattern, response in INFO_PATTERNS:
            if re.search(pattern, text_lower):
                yield AgentEvent(type="thought", content="Recognized greeting/help request")
                yield AgentEvent(type="final_response", content=response)
                return
        
        # Check for command patterns
        for pattern, tool_name, command_template, reason in COMMAND_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                # Expand command template with captured groups
                try:
                    command = re.sub(pattern, command_template, text_lower)
                    # Clean up command
                    command = command.strip()
                    if command == text_lower:
                        command = command_template
                except:
                    command = command_template
                
                yield AgentEvent(type="thought", content=f"Matched pattern: {reason}")
                yield AgentEvent(
                    type="tool_request",
                    content=command,
                    tool_call={
                        "name": tool_name,
                        "command": command,
                        "reason": reason,
                    }
                )
                return
        
        # No pattern matched - suggest help
        yield AgentEvent(
            type="thought", 
            content="No pattern matched. Suggesting help."
        )
        yield AgentEvent(
            type="final_response",
            content=f"I don't understand '{user_text[:50]}...' in LOCAL mode.\n\nTry:\n- 'list files' - show directory\n- 'read filename.py' - read file\n- 'git status' - check git\n- 'help' - show all commands\n\nFor smarter responses, configure OPENROUTER_API_KEY or AGENTZERO_API_URL."
        )
    
    async def explain_risk(self, command: str) -> str:
        """Analyze command risk with templates."""
        cmd_lower = command.lower()
        
        for keyword, risk in RISK_TEMPLATES.items():
            if keyword in cmd_lower:
                return f"Command: {command}\n\n{risk}"
        
        return f"Command: {command}\n\n{RISK_TEMPLATES['default']}"
    
    async def execute_tool(self, tool_name: str, command: str, cwd: str | None = None) -> AsyncGenerator[AgentEvent, None]:
        """Execute tool (real execution)."""
        from .tools.executor import execute_tool as real_execute
        
        async for event in real_execute(tool_name, command, cwd):
            yield AgentEvent(
                type=event.get("type", "status"),
                content=event.get("content", "")
            )
    
    async def close(self):
        """No cleanup needed for local backend."""
        pass
    
    def get_stats(self) -> dict:
        """Get backend statistics."""
        return {
            "backend": "Local (Deterministic)",
            "patterns": len(COMMAND_PATTERNS),
            "history_length": len(self.history),
        }


def create_backend() -> LocalBackend:
    """Create a local deterministic backend."""
    return LocalBackend()
