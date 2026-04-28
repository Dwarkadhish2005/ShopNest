from __future__ import annotations

from threading import RLock
from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class InMemorySessionStore:
    """Thread-safe in-memory chat history for API sessions."""

    def __init__(self, max_turns: int = 12) -> None:
        self._sessions: Dict[str, List[BaseMessage]] = {}
        self._lock = RLock()
        self._max_messages = max_turns * 2

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def append_turn(self, session_id: str, user_text: str, assistant_text: str) -> None:
        with self._lock:
            messages = self._sessions.setdefault(session_id, [])
            messages.append(HumanMessage(content=user_text))
            messages.append(AIMessage(content=assistant_text))
            if len(messages) > self._max_messages:
                self._sessions[session_id] = messages[-self._max_messages :]

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            existed = session_id in self._sessions
            self._sessions.pop(session_id, None)
            return existed

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions
