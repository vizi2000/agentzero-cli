"""Chat session management for AgentZeroCLI."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ChatMessage:
    """Single chat message."""

    role: str  # "user", "agent", "system", "tool", "thinking"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Represents a single chat session/conversation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "New Chat"
    messages: list[ChatMessage] = field(default_factory=list)
    context_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = False

    def add_message(self, role: str, content: str, **metadata) -> ChatMessage:
        """Add a message to this session."""
        msg = ChatMessage(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        return msg

    def clear(self) -> None:
        """Clear all messages and reset context."""
        self.messages.clear()
        self.context_id = None

    def get_last_message(self, role: str | None = None) -> ChatMessage | None:
        """Get the last message, optionally filtered by role."""
        if role:
            for msg in reversed(self.messages):
                if msg.role == role:
                    return msg
            return None
        return self.messages[-1] if self.messages else None

    def message_count(self) -> int:
        return len(self.messages)


class SessionManager:
    """Manages multiple chat sessions."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}
        self._active_id: str | None = None
        self._create_default_session()

    def _create_default_session(self) -> None:
        session = self.create_session("Chat 1")
        self.set_active(session.id)

    def create_session(self, name: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(name=name)
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def get_active(self) -> ChatSession | None:
        """Get the currently active session."""
        if self._active_id:
            return self._sessions.get(self._active_id)
        return None

    def set_active(self, session_id: str) -> bool:
        """Set the active session."""
        if session_id in self._sessions:
            if self._active_id:
                prev = self._sessions.get(self._active_id)
                if prev:
                    prev.is_active = False
            self._active_id = session_id
            self._sessions[session_id].is_active = True
            return True
        return False

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session."""
        if len(self._sessions) <= 1:
            return False  # Keep at least one session
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_id == session_id:
                self._active_id = next(iter(self._sessions.keys()), None)
                if self._active_id:
                    self._sessions[self._active_id].is_active = True
            return True
        return False

    def list_sessions(self) -> list[ChatSession]:
        """List all sessions ordered by creation time."""
        return sorted(self._sessions.values(), key=lambda s: s.created_at)

    def session_count(self) -> int:
        return len(self._sessions)

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a session."""
        session = self._sessions.get(session_id)
        if session:
            session.name = new_name
            return True
        return False
