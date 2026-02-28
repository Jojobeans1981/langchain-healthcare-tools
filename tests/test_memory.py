"""Isolated unit tests for AgentForge conversation memory.

Tests session history management, clearing, and trimming — no API keys needed.
Global state is auto-cleaned by conftest.py fixtures.
"""

import pytest

from app.agent.memory import (
    MAX_HISTORY_MESSAGES,
    clear_session,
    get_session_history,
    trim_history,
)


class TestGetSessionHistory:
    def test_creates_new_session(self):
        history = get_session_history("test-new-session")
        assert history is not None
        assert len(history.messages) == 0

    def test_returns_same_instance(self):
        h1 = get_session_history("test-same-instance")
        h2 = get_session_history("test-same-instance")
        assert h1 is h2

    def test_different_sessions_are_independent(self):
        ha = get_session_history("test-session-a")
        hb = get_session_history("test-session-b")
        ha.add_user_message("hello from A")

        assert len(ha.messages) == 1
        assert len(hb.messages) == 0


class TestClearSession:
    def test_clear_existing_session(self):
        history = get_session_history("test-clear")
        history.add_user_message("msg1")
        history.add_ai_message("reply1")
        assert len(history.messages) == 2

        clear_session("test-clear")
        new_history = get_session_history("test-clear")
        assert len(new_history.messages) == 0

    def test_clear_nonexistent_session(self):
        clear_session("nonexistent-session-xyz")

    def test_new_session_after_clear(self):
        history = get_session_history("test-clear-recreate")
        history.add_user_message("old message")
        clear_session("test-clear-recreate")

        new_history = get_session_history("test-clear-recreate")
        assert len(new_history.messages) == 0


class TestTrimHistory:
    def test_no_trim_under_limit(self):
        history = get_session_history("test-no-trim")
        history.add_user_message("msg1")
        history.add_ai_message("reply1")

        trim_history("test-no-trim")
        assert len(history.messages) == 2

    def test_trims_to_max(self):
        sid = "test-trim-max"
        history = get_session_history(sid)

        for i in range(MAX_HISTORY_MESSAGES + 10):
            history.add_user_message(f"msg-{i}")

        assert len(history.messages) > MAX_HISTORY_MESSAGES
        trim_history(sid)
        assert len(history.messages) == MAX_HISTORY_MESSAGES

    def test_keeps_most_recent(self):
        sid = "test-trim-recent"
        history = get_session_history(sid)

        for i in range(MAX_HISTORY_MESSAGES + 5):
            history.add_user_message(f"msg-{i}")

        trim_history(sid)
        last_msg = history.messages[-1]
        assert f"msg-{MAX_HISTORY_MESSAGES + 4}" in last_msg.content

    def test_trim_nonexistent_session(self):
        trim_history("nonexistent-session-trim")
