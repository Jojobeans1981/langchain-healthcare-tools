import threading
import time

from langchain_core.chat_history import InMemoryChatMessageHistory

# Session-based conversation memory store
_session_histories: dict[str, InMemoryChatMessageHistory] = {}
_session_last_access: dict[str, float] = {}

# Thread safety lock for session store (Phase 4A)
_lock = threading.Lock()

MAX_HISTORY_MESSAGES = 20  # Keep last 20 messages (10 turns)
MAX_SESSIONS = 100  # Prevent unbounded memory growth
SESSION_TTL_SECONDS = 3600  # Expire sessions after 1 hour of inactivity


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Get or create a conversation history for a session.

    Enforces invariants:
    - Max sessions capped to prevent memory leaks
    - Stale sessions evicted after TTL
    - Each session_id gets its own isolated history
    - Thread-safe: uses a lock to prevent concurrent corruption
    """
    with _lock:
        _evict_stale_sessions()

        if session_id not in _session_histories:
            # If at capacity, evict oldest session
            if len(_session_histories) >= MAX_SESSIONS:
                oldest_id = min(_session_last_access, key=_session_last_access.get)
                _clear_session_unlocked(oldest_id)
            _session_histories[session_id] = InMemoryChatMessageHistory()

        _session_last_access[session_id] = time.time()
        return _session_histories[session_id]


def clear_session(session_id: str) -> None:
    """Clear conversation history for a session (thread-safe)."""
    with _lock:
        _clear_session_unlocked(session_id)


def _clear_session_unlocked(session_id: str) -> None:
    """Clear session without acquiring lock (caller must hold _lock)."""
    _session_histories.pop(session_id, None)
    _session_last_access.pop(session_id, None)


def trim_history(session_id: str) -> None:
    """Trim conversation history to keep only recent messages."""
    if session_id in _session_histories:
        history = _session_histories[session_id]
        messages = history.messages
        if len(messages) > MAX_HISTORY_MESSAGES:
            history.clear()
            for msg in messages[-MAX_HISTORY_MESSAGES:]:
                history.add_message(msg)


def _evict_stale_sessions() -> None:
    """Remove sessions that haven't been accessed within the TTL.

    Note: Caller must hold _lock since this is called from get_session_history.
    """
    now = time.time()
    stale = [
        sid for sid, last in _session_last_access.items()
        if now - last > SESSION_TTL_SECONDS
    ]
    for sid in stale:
        _clear_session_unlocked(sid)
