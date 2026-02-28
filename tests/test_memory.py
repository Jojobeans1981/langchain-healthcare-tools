"""Isolated unit tests for AgentForge conversation memory.

Tests session history management, clearing, and trimming — no API keys needed.
"""

import pytest

from app.agent.memory import (
    MAX_HISTORY_MESSAGES,
    _session_histories,
    clear_session,
    get_session_history,
    trim_history,
)


class TestGetSessionHistory:
    def test_creates_new_session(self):
        sid = "test-new-session"
        _session_histories.pop(sid, None)  # ensure clean
        history = get_session_history(sid)
        assert history is not None
        assert len(history.messages) == 0
        _session_histories.pop(sid, None)

    def test_returns_same_instance(self):
        sid = "test-same-instance"
        _session_histories.pop(sid, None)
        h1 = get_session_history(sid)
        h2 = get_session_history(sid)
        assert h1 is h2
        _session_histories.pop(sid, None)

    def test_different_sessions_are_independent(self):
        sid_a = "test-session-a"
        sid_b = "test-session-b"
        _session_histories.pop(sid_a, None)
        _session_histories.pop(sid_b, None)

        ha = get_session_history(sid_a)
        hb = get_session_history(sid_b)
        ha.add_user_message("hello from A")

        assert len(ha.messages) == 1
        assert len(hb.messages) == 0

        _session_histories.pop(sid_a, None)
        _session_histories.pop(sid_b, None)


class TestClearSession:
    def test_clear_existing_session(self):
        sid = "test-clear"
        _session_histories.pop(sid, None)
        history = get_session_history(sid)
        history.add_user_message("msg1")
        history.add_ai_message("reply1")
        assert len(history.messages) == 2

        clear_session(sid)
        assert sid not in _session_histories

    def test_clear_nonexistent_session(self):
        # Should not raise
        clear_session("nonexistent-session-xyz")

    def test_new_session_after_clear(self):
        sid = "test-clear-recreate"
        _session_histories.pop(sid, None)
        history = get_session_history(sid)
        history.add_user_message("old message")
        clear_session(sid)

        new_history = get_session_history(sid)
        assert len(new_history.messages) == 0
        _session_histories.pop(sid, None)


class TestTrimHistory:
    def test_no_trim_under_limit(self):
        sid = "test-no-trim"
        _session_histories.pop(sid, None)
        history = get_session_history(sid)
        history.add_user_message("msg1")
        history.add_ai_message("reply1")

        trim_history(sid)
        assert len(history.messages) == 2
        _session_histories.pop(sid, None)

    def test_trims_to_max(self):
        sid = "test-trim-max"
        _session_histories.pop(sid, None)
        history = get_session_history(sid)

        # Add more than MAX_HISTORY_MESSAGES
        for i in range(MAX_HISTORY_MESSAGES + 10):
            history.add_user_message(f"msg-{i}")

        assert len(history.messages) > MAX_HISTORY_MESSAGES
        trim_history(sid)
        assert len(history.messages) == MAX_HISTORY_MESSAGES
        _session_histories.pop(sid, None)

    def test_keeps_most_recent(self):
        sid = "test-trim-recent"
        _session_histories.pop(sid, None)
        history = get_session_history(sid)

        for i in range(MAX_HISTORY_MESSAGES + 5):
            history.add_user_message(f"msg-{i}")

        trim_history(sid)
        # Last message should be the most recent one
        last_msg = history.messages[-1]
        assert f"msg-{MAX_HISTORY_MESSAGES + 4}" in last_msg.content
        _session_histories.pop(sid, None)

    def test_trim_nonexistent_session(self):
        # Should not raise
        trim_history("nonexistent-session-trim")
