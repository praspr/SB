"""Shared test fixtures for sb-todos."""

import sqlite3

import pytest

from sb_todos.db import run_migrations


@pytest.fixture
def conn():
    """In-memory SQLite connection with migrations applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    run_migrations(c)
    yield c
    c.close()
