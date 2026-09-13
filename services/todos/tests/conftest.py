"""Shared test fixtures for sb-todos."""

import sqlite3

import pytest

from sb_todos import db as db_module
from sb_todos.db import connect, run_migrations


@pytest.fixture
def conn():
    """In-memory SQLite connection with migrations applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """FastAPI TestClient wired to a temp SQLite DB file."""
    db_path = tmp_path / "todos.db"
    monkeypatch.setenv("SB_TODOS_DB_PATH", str(db_path))

    # Reset any cached settings/connection singletons so the new env var takes effect.
    db_module.reset_conn()
    import sb_todos.config as config_module

    config_module.settings = config_module.Settings()

    # Patch the settings reference used inside db.get_conn (imported lazily there,
    # but main.py imports settings at module load time too) -- reload main.
    import importlib

    import sb_todos.main as main_module

    importlib.reload(main_module)

    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        yield client

    db_module.reset_conn()
