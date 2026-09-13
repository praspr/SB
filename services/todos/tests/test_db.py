"""Tests for the migration runner in db.py."""

import sqlite3

from sb_todos.db import run_migrations


def test_migrations_create_tables():
    conn = sqlite3.connect(":memory:")
    run_migrations(conn)

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "todos" in tables
    assert "schema_migrations" in tables

    versions = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    assert versions == {1}
    conn.close()


def test_migrations_idempotent():
    conn = sqlite3.connect(":memory:")
    run_migrations(conn)
    run_migrations(conn)  # should not raise or duplicate

    versions = conn.execute("SELECT version FROM schema_migrations").fetchall()
    assert len(versions) == 1
    conn.close()


def test_todos_table_columns(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(todos)").fetchall()}
    expected = {
        "id",
        "title",
        "description",
        "priority",
        "due_date",
        "due_time",
        "is_completed",
        "completed_at",
        "tags",
        "external_source",
        "external_ref",
        "domain",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(cols)
