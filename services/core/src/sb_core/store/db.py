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


def _m6_proposals(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_proposals (
          id          INTEGER PRIMARY KEY AUTOINCREMENT,
          kind        TEXT NOT NULL,
          title       TEXT NOT NULL,
          body        TEXT NOT NULL DEFAULT '',
          status      TEXT NOT NULL DEFAULT 'pending',
          signal_refs TEXT NOT NULL DEFAULT '[]',
          created_at  TEXT NOT NULL DEFAULT (datetime('now')),
          decided_at  TEXT,
          target_path TEXT,
          updated_at  TEXT
        )
        """)
    _add_column(conn, "sb_proposals", "target_path", "TEXT")
    _add_column(conn, "sb_proposals", "updated_at", "TEXT")


def _m7_webex(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_webex_meetings (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          start_at TEXT NOT NULL,
          end_at TEXT NOT NULL,
          join_url TEXT,
          organizer TEXT,
          attendees TEXT NOT NULL DEFAULT '[]',
          agenda TEXT,
          synced_at TEXT NOT NULL
        )
        """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_webex_spaces (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          is_dm INTEGER NOT NULL DEFAULT 0,
          unread_count INTEGER NOT NULL DEFAULT 0,
          last_activity TEXT,
          members_count INTEGER NOT NULL DEFAULT 0,
          synced_at TEXT NOT NULL
        )
        """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_webex_messages (
          id TEXT PRIMARY KEY,
          space_id TEXT NOT NULL,
          space_name TEXT NOT NULL,
          sender_name TEXT NOT NULL,
          sender_email TEXT,
          is_dm INTEGER NOT NULL DEFAULT 0,
          is_mention INTEGER NOT NULL DEFAULT 0,
          is_unread INTEGER NOT NULL DEFAULT 0,
          preview TEXT NOT NULL,
          occurred_at TEXT NOT NULL,
          deep_link TEXT,
          synced_at TEXT NOT NULL
        )
        """)


def _m8_ledger(conn: sqlite3.Connection) -> None:
    """Append-only narrative ledger, session cache, and project registry."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_ledger (
          id             INTEGER PRIMARY KEY AUTOINCREMENT,
          ts             TEXT    NOT NULL,
          session_id     TEXT    NOT NULL,
          project        TEXT    NOT NULL,
          scope          TEXT,
          action_verb    TEXT    NOT NULL,
          summary        TEXT    NOT NULL,
          body           TEXT,
          refs           TEXT    NOT NULL DEFAULT '[]',
          source_harness TEXT    NOT NULL,
          agent_model    TEXT,
          working_dir    TEXT,
          origin         TEXT    NOT NULL,
          redaction_applied       INTEGER NOT NULL DEFAULT 0,
          redaction_rules_version INTEGER NOT NULL DEFAULT 0,
          content_sha256 TEXT    NOT NULL,
          created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_ts ON sb_ledger(ts DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_project ON sb_ledger(project, ts DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_session ON sb_ledger(session_id, ts)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_verb ON sb_ledger(action_verb, ts DESC)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_dedup ON sb_ledger(content_sha256)"
    )

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS sb_ledger_fts USING fts5(
          summary, body, project, scope, action_verb, refs,
          content='sb_ledger', content_rowid='id', tokenize='porter'
        )
        """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS sb_ledger_ai AFTER INSERT ON sb_ledger BEGIN
          INSERT INTO sb_ledger_fts(rowid, summary, body, project, scope, action_verb, refs)
          VALUES (new.id, new.summary, new.body, new.project, new.scope, new.action_verb, new.refs);
        END
        """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS sb_ledger_no_update BEFORE UPDATE ON sb_ledger
          BEGIN SELECT RAISE(ABORT, 'sb_ledger is append-only'); END
        """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS sb_ledger_no_delete BEFORE DELETE ON sb_ledger
          BEGIN SELECT RAISE(ABORT, 'sb_ledger is append-only'); END
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_ledger_sessions (
          session_id   TEXT PRIMARY KEY,
          started_at   TEXT NOT NULL,
          agent        TEXT,
          working_dir  TEXT,
          project      TEXT,
          extras       TEXT NOT NULL DEFAULT '{}'
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_project_registry (
          project        TEXT PRIMARY KEY,
          root_path      TEXT NOT NULL,
          changelog_path TEXT NOT NULL,
          sync_mode      TEXT NOT NULL DEFAULT 'dual',
          added_at       TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)


def _m9_batch(conn: sqlite3.Connection) -> None:
    """Muted Webex spaces, the scheduled-rituals engine, and the DB-backed
    goals registry (phase 2a: quick wins + goals + automation)."""
    _add_column(conn, "sb_webex_spaces", "muted", "INTEGER NOT NULL DEFAULT 0")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_scheduled_rituals (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          name         TEXT NOT NULL,
          ritual       TEXT NOT NULL,
          args_json    TEXT NOT NULL DEFAULT '{}',
          cron         TEXT NOT NULL,
          target_dir   TEXT,
          enabled      INTEGER NOT NULL DEFAULT 1,
          last_run_at  TEXT,
          last_status  TEXT,
          created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_goals_registry (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          tier         TEXT NOT NULL,
          title        TEXT NOT NULL,
          description  TEXT,
          keywords     TEXT NOT NULL DEFAULT '[]',
          target_date  TEXT,
          status       TEXT NOT NULL DEFAULT 'active',
          created_at   TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at   TEXT
        )
        """)


def _m10_webex_threads(conn: sqlite3.Connection) -> None:
    """Parent-message metadata for reply-to-me detection, plus the cached
    Webex identity (phase 2c)."""
    _add_column(conn, "sb_webex_messages", "parent_message_id", "TEXT")
    _add_column(conn, "sb_webex_messages", "parent_sender_email", "TEXT")
    _add_column(
        conn, "sb_webex_messages", "is_reply_to_me", "INTEGER NOT NULL DEFAULT 0"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sb_webex_identity (
          email        TEXT PRIMARY KEY,
          display_name TEXT,
          cached_at    TEXT NOT NULL
        )
        """)


_MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, _m1_metadata),
    (2, _m2_skills),
    (3, _m3_signals),
    (4, _m4_sync_state),
    (5, _m5_daily),
    (6, _m6_proposals),
    (7, _m7_webex),
    (8, _m8_ledger),
    (9, _m9_batch),
    (10, _m10_webex_threads),
]

_REQUIRED_COLUMNS: dict[str, dict[str, str]] = {
    "sb_daily": {
        "plan_md": "TEXT",
        "plan_data": "TEXT",
        "wrap_md": "TEXT",
        "wrap_data": "TEXT",
    },
    "sb_proposals": {
        "target_path": "TEXT",
        "updated_at": "TEXT",
    },
    "sb_webex_spaces": {
        "muted": "INTEGER NOT NULL DEFAULT 0",
    },
    "sb_webex_messages": {
        "parent_message_id": "TEXT",
        "parent_sender_email": "TEXT",
        "is_reply_to_me": "INTEGER NOT NULL DEFAULT 0",
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
