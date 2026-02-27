from langchain_core.chat_history import InMemoryChatMessageHistory

# Session-based conversation memory store
_session_histories: dict[str, InMemoryChatMessageHistory] = {}

MAX_HISTORY_MESSAGES = 20  # Keep last 20 messages (10 turns)


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Get or create a conversation history for a session."""
    if session_id not in _session_histories:
        _session_histories[session_id] = InMemoryChatMessageHistory()
    return _session_histories[session_id]


def clear_session(session_id: str) -> None:
    """Clear conversation history for a session."""
    _session_histories.pop(session_id, None)


def trim_history(session_id: str) -> None:
    """Trim conversation history to keep only recent messages."""
    if session_id in _session_histories:
        history = _session_histories[session_id]
        messages = history.messages
        if len(messages) > MAX_HISTORY_MESSAGES:
            history.clear()
            for msg in messages[-MAX_HISTORY_MESSAGES:]:
                history.add_message(msg)
