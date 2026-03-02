"""SQLite database module for AgentForge stateful operations.

Provides persistent storage for patient medication watchlists
and other CRUD-backed features.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "agentforge.db"


def get_db(db_path: Path = None) -> sqlite3.Connection:
    """Get a database connection. Uses DB_PATH by default."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Path = None):
    """Initialize database schema."""
    conn = get_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patient_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            medication_name TEXT NOT NULL,
            added_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            UNIQUE(patient_id, medication_name)
        )
    """)
    # Add last_scanned column if missing (safe for existing DBs)
    try:
        conn.execute("ALTER TABLE patient_watchlist ADD COLUMN last_scanned TEXT DEFAULT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Add source column if missing — tracks 'manual' vs 'openemr' origin
    try:
        conn.execute("ALTER TABLE patient_watchlist ADD COLUMN source TEXT DEFAULT 'manual'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


init_db()
