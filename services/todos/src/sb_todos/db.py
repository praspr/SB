"""SQLite connection management and migration runner for sb-todos."""

from __future__ import annotations

import glob
import os
import sqlite3
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_conn: sqlite3.Connection | None = None


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")


def run_migrations(conn: sqlite3.Connection) -> None:
    """Bootstrap schema_migrations table and apply any unapplied migrations."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    migration_files = sorted(glob.glob(str(_MIGRATIONS_DIR / "*.sql")))
    for path in migration_files:
        filename = os.path.basename(path)
        version_str = filename.split("_", 1)[0]
        try:
            version = int(version_str)
        except ValueError:
            continue
        if version in applied:
            continue

        sql = Path(path).read_text()
        for statement in sql.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc):
                    continue
                raise
        conn.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a new connection to the given path, ensuring parent dirs exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    _configure_connection(conn)
    run_migrations(conn)
    return conn


def get_conn() -> sqlite3.Connection:
    """Return the process-wide singleton connection, opening it on first use."""
    global _conn
    if _conn is None:
        from .config import settings

        _conn = connect(settings.db_path)
    return _conn


def reset_conn() -> None:
    """Close and clear the singleton connection (mainly for tests)."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
