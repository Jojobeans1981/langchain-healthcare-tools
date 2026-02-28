"""Shared test fixtures for AgentForge test suite.

Provides automatic cleanup of global state and reusable test helpers
so individual test files don't need manual teardown.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.agent.memory import _session_histories, _session_last_access
from app.observability import _traces, _feedback


@pytest.fixture(autouse=True)
def _isolate_memory():
    """Snapshot and restore session memory around every test.

    Prevents cross-test contamination from leftover sessions.
    """
    snapshot_histories = dict(_session_histories)
    snapshot_access = dict(_session_last_access)
    yield
    _session_histories.clear()
    _session_histories.update(snapshot_histories)
    _session_last_access.clear()
    _session_last_access.update(snapshot_access)


@pytest.fixture(autouse=True)
def _isolate_traces():
    """Snapshot, clear, and restore observability traces around every test.

    Each test starts with clean trace/feedback state.
    """
    snapshot_traces = list(_traces)
    snapshot_feedback = list(_feedback)
    _traces.clear()
    _feedback.clear()
    yield
    _traces.clear()
    _traces.extend(snapshot_traces)
    _feedback.clear()
    _feedback.extend(snapshot_feedback)


@pytest.fixture()
def tmp_db():
    """Provide a temporary SQLite database path, cleaned up after test."""
    from app.database import init_db
    db_path = Path(tempfile.mkdtemp()) / "test_agentforge.db"
    init_db(db_path)
    yield db_path
    if db_path.exists():
        os.unlink(db_path)
