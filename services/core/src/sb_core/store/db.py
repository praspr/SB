"""SQLite connection management and migrations for core.db.

Design:
- No process-wide singleton; callers open a fresh connection per operation.
- check_same_thread is left at its default (True) — connections must not cross
  thread or process boundaries.
- WAL mode + busy_timeout make concurrent readers/writers safe.
- Each migration (schema change + version record) is applied atomically inside a
  single ``BEGIN IMMEDIATE`` transaction.  Schema changes are written to be
  idempotent, so a process that crashed after the DDL but before recording the
  version recovers cleanly on the next run.  Bootstrap is serialized with
  ``BEGIN IMMEDIATE`` + busy_timeout and a bounded retry loop.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Callable

_BUSY_TIMEOUT_MS = 5000
_MIGRATION_RETRIES = 10
_MIGRATION_BACKOFF_S = 0.05


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """Add *column* to *table* only if it does not already exist (idempotent)."""
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _m1_metadata(conn: sqlite3.Connection) -> None:
    """Foundation metadata only. Domain tables arrive in later steps."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_meta (
          key   TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """)
    conn.execute(
        "INSERT OR IGNORE INTO sb_meta (key, value) VALUES ('component', 'sb-core')"
    )


def _m2_skills(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_skills (
          id              TEXT PRIMARY KEY,
          name            TEXT NOT NULL,
          description     TEXT NOT NULL DEFAULT '',
          source          TEXT NOT NULL,
          path            TEXT NOT NULL,
          content_sha256  TEXT NOT NULL DEFAULT '',
          modified_at     TEXT,
          synced_at       TEXT NOT NULL,
          enabled         INTEGER NOT NULL DEFAULT 1,
          available       INTEGER NOT NULL DEFAULT 1,
          allowed_tools   TEXT NOT NULL DEFAULT '[]',
          procedure       TEXT NOT NULL DEFAULT ''
        )
        """)


def _m3_signals(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_signals (
          id          INTEGER PRIMARY KEY AUTOINCREMENT,
          source      TEXT    NOT NULL,
          source_id   TEXT    NOT NULL,
          kind        TEXT    NOT NULL,
          occurred_at TEXT    NOT NULL,
          title       TEXT    NOT NULL,
          body        TEXT,
          scope       TEXT,
          verb        TEXT,
          refs        TEXT    NOT NULL DEFAULT '[]',
          raw_ref     TEXT,
          created_at  TEXT    NOT NULL,
          UNIQUE(source, source_id)
        )
        """)


def _m4_sync_state(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_sync_state (
          adapter      TEXT PRIMARY KEY,
          last_run_at  TEXT NOT NULL,
          signal_count INTEGER NOT NULL DEFAULT 0,
          error        TEXT
        )
        """)


def _m5_daily(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_daily (
          date       TEXT PRIMARY KEY,
          payload    TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          plan_md    TEXT,
          plan_data  TEXT,
          wrap_md    TEXT,
          wrap_data  TEXT
        )
        """)
    _add_column(conn, "sb_daily", "plan_md", "TEXT")
    _add_column(conn, "sb_daily", "plan_data", "TEXT")
    _add_column(conn, "sb_daily", "wrap_md", "TEXT")
    _add_column(conn, "sb_daily", "wrap_data", "TEXT")


_MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, _m1_metadata),
    (2, _m2_skills),
    (3, _m3_signals),
    (4, _m4_sync_state),
    (5, _m5_daily),
]

_REQUIRED_COLUMNS: dict[str, dict[str, str]] = {
    "sb_daily": {
        "plan_md": "TEXT",
        "plan_data": "TEXT",
        "wrap_md": "TEXT",
        "wrap_data": "TEXT",
    },
}


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")


def _is_locked(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


def _in_immediate_txn(conn: sqlite3.Connection, work: Callable[[], None]) -> None:
    """Run *work* inside a serialized ``BEGIN IMMEDIATE`` transaction with retry."""
    last_exc: sqlite3.OperationalError | None = None
    for attempt in range(_MIGRATION_RETRIES):
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                work()
            except Exception:
                conn.rollback()
                raise
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            if not _is_locked(exc):
                raise
            last_exc = exc
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                pass
            time.sleep(_MIGRATION_BACKOFF_S * (attempt + 1))
    if last_exc is not None:
        raise last_exc


def schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 when none are recorded."""
    row = conn.execute(
        "SELECT MAX(version) AS version FROM core_schema_migrations"
    ).fetchone()
    if row is None or row["version"] is None:
        return 0
    return int(row["version"])


def run_migrations(conn: sqlite3.Connection) -> None:
    """Bootstrap the migrations table and apply any unapplied migrations.

    Safe to run concurrently from multiple connections: writes are serialized
    via ``BEGIN IMMEDIATE`` + busy_timeout, and every schema step is idempotent.
    """

    def _bootstrap() -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core_schema_migrations (
              version    INTEGER PRIMARY KEY,
              applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """)

    _in_immediate_txn(conn, _bootstrap)

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM core_schema_migrations").fetchall()
    }

    for version, migrate in _MIGRATIONS:
        if version in applied:
            continue

        def _apply(
            migrate: Callable[[sqlite3.Connection], None] = migrate,
            version: int = version,
        ) -> None:
            migrate(conn)
            conn.execute(
                "INSERT OR IGNORE INTO core_schema_migrations (version) VALUES (?)",
                (version,),
            )

        _in_immediate_txn(conn, _apply)

    _ensure_required_columns(conn)


def _ensure_required_columns(conn: sqlite3.Connection) -> None:
    """Add any required columns missing after a partial migration.

    Skips tables that do not exist yet so an earlier schema can start cleanly.
    """
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    for table, columns in _REQUIRED_COLUMNS.items():
        if table not in existing_tables:
            continue
        present = _columns(conn, table)
        missing = {c: decl for c, decl in columns.items() if c not in present}
        if not missing:
            continue

        def _add_missing(table: str = table, missing: dict[str, str] = missing) -> None:
            for column, decl in missing.items():
                _add_column(conn, table, column, decl)

        _in_immediate_txn(conn, _add_missing)


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open (or create) a WAL SQLite DB at *db_path*, run migrations, and return
    a fresh connection.

    Each caller should open its own connection and close it when done.
    Do not share connections across threads or processes.
    """
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=_BUSY_TIMEOUT_MS / 1000)
    _configure(conn)
    run_migrations(conn)
    return conn
