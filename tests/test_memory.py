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


# ===================================================================
# Phase 4B: Thread Safety Tests
# ===================================================================


class TestThreadSafety:
    def test_concurrent_session_access(self):
        """Multiple threads accessing the same session shouldn't corrupt state."""
        import threading

        errors = []

        def add_messages(session_id, count):
            try:
                history = get_session_history(session_id)
                for i in range(count):
                    history.add_user_message(f"msg-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_messages, args=("test-thread-safety", 50)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_concurrent_different_sessions(self):
        """Multiple threads accessing different sessions simultaneously."""
        import threading

        errors = []

        def create_session(session_id):
            try:
                history = get_session_history(session_id)
                history.add_user_message(f"hello from {session_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_session, args=(f"thread-{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_concurrent_clear_and_access(self):
        """Clearing a session while another thread accesses it shouldn't crash."""
        import threading

        errors = []
        get_session_history("test-clear-race")

        def access_session():
            try:
                for _ in range(20):
                    get_session_history("test-clear-race")
            except Exception as e:
                errors.append(e)

        def clear_session_repeatedly():
            try:
                for _ in range(20):
                    clear_session("test-clear-race")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=access_session)
        t2 = threading.Thread(target=clear_session_repeatedly)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(errors) == 0
