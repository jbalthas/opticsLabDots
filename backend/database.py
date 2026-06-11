"""
database.py — SQLite schema and connection management for OLB.

Tables:
  sessions        — lab sessions (QA / PIV / Research)
  session_steps   — 13-step QA setup checklist per session
  session_log     — free-form timestamped log entries
  captures        — individual image captures
  analysis_runs   — analysis engine results (IQ-Analyzer X, custom, MATLAB)
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

# Thread-local storage so each thread gets its own connection.
_local = threading.local()
_DB_PATH: Path | None = None


def init_db(db_path: Path) -> None:
    """Create tables if they don't exist. Call once at app startup."""
    global _DB_PATH
    _DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        _create_schema(conn)


def get_conn() -> sqlite3.Connection:
    """Return a per-thread SQLite connection (auto-created on first call)."""
    if not hasattr(_local, "conn") or _local.conn is None:
        assert _DB_PATH is not None, "init_db() must be called before get_conn()"
        _local.conn = _connect(_DB_PATH)
    return _local.conn


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    """Add a column to a table if it doesn't already exist (safe re-entrant migration)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id          TEXT PRIMARY KEY,
        mode        TEXT NOT NULL CHECK(mode IN ('QA','PIV','Research')),
        camera_id   TEXT,
        chart_type  TEXT,
        rail_stop   INTEGER,
        operator    TEXT,
        notes       TEXT,
        started_at  TEXT NOT NULL,
        ended_at    TEXT,
        status      TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','completed','aborted'))
    );

    CREATE TABLE IF NOT EXISTS session_steps (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES sessions(id),
        step_num    INTEGER NOT NULL,
        step_name   TEXT NOT NULL,
        completed   INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT,
        notes       TEXT
    );

    CREATE TABLE IF NOT EXISTS session_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES sessions(id),
        timestamp   TEXT NOT NULL,
        level       TEXT NOT NULL DEFAULT 'info' CHECK(level IN ('info','warn','error')),
        message     TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS captures (
        id          TEXT PRIMARY KEY,
        session_id  TEXT REFERENCES sessions(id),
        camera_id   TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        file_path   TEXT NOT NULL,
        format      TEXT NOT NULL DEFAULT 'jpeg',
        width       INTEGER,
        height      INTEGER,
        file_size   INTEGER,
        label       TEXT,
        rail_stop   INTEGER,
        metadata    TEXT
    );

    CREATE TABLE IF NOT EXISTS analysis_runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        capture_id  TEXT NOT NULL REFERENCES captures(id),
        engine      TEXT NOT NULL CHECK(engine IN ('iqanalyzer','custom','matlab')),
        profile     TEXT,
        status      TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','running','completed','failed')),
        started_at  TEXT,
        completed_at TEXT,
        results_path TEXT,
        results_json TEXT,
        error_msg   TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_captures_session    ON captures(session_id);
    CREATE INDEX IF NOT EXISTS idx_analysis_capture    ON analysis_runs(capture_id);
    CREATE INDEX IF NOT EXISTS idx_session_log_session ON session_log(session_id);
    CREATE INDEX IF NOT EXISTS idx_steps_session       ON session_steps(session_id);
    """)
    conn.commit()

    # Safe schema migrations — add columns introduced after initial deployment
    _migrate_add_column(conn, "analysis_runs", "test_id", "TEXT")
