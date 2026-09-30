"""Focused contract tests for the standalone Step 1 core service."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from sb_core import __version__
from sb_core.config import Settings
from sb_core.main import app
from sb_core.mcp_app import mcp, system_status
from sb_core.store.db import connect, run_migrations


def test_core_defaults_and_database_env_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SB_CORE_CONFIG_PATH", raising=False)
    monkeypatch.delenv("SB_CORE_HOST", raising=False)
    monkeypatch.delenv("SB_CORE_PORT", raising=False)
    monkeypatch.delenv("SB_CORE_DB_PATH", raising=False)

    defaults = Settings()
    assert defaults.host == "127.0.0.1"
    assert defaults.port == 8787
    assert defaults.db_path.expanduser() == Path.home() / ".local/share/sb/core.db"

    custom_path = tmp_path / "foundation.db"
    monkeypatch.setenv("SB_CORE_DB_PATH", str(custom_path))
    assert Settings().db_path == custom_path


def test_database_is_ready_and_migrations_are_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    run_migrations(conn)
    run_migrations(conn)

    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    versions = [
        row[0]
        for row in conn.execute(
            "SELECT version FROM core_schema_migrations ORDER BY version"
        ).fetchall()
    ]
    assert versions == [1, 2, 3, 4]
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "sb_meta" in tables
    assert "sb_skills" in tables
    assert "sb_signals" in tables
    assert "sb_sync_state" in tables
    assert "core_schema_migrations" in tables
    for later in ("sb_daily", "sb_proposals"):
        assert later not in tables
    conn.close()


def test_migrations_are_concurrency_safe(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    errors: list[BaseException] = []

    def _open() -> None:
        try:
            conn = connect(db_path)
            conn.close()
        except BaseException as exc:  # noqa: BLE001 — collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=_open) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    conn = connect(db_path)
    versions = [
        row[0]
        for row in conn.execute(
            "SELECT version FROM core_schema_migrations ORDER BY version"
        ).fetchall()
    ]
    assert versions == [1, 2, 3, 4]
    conn.close()


def test_system_status_reports_readiness() -> None:
    async def inspect() -> tuple[set[str], int, int]:
        tools = await mcp.list_tools()
        prompts = await mcp.list_prompts()
        resources = await mcp.list_resources()
        names = {tool.name for tool in tools}

        assert "system_status" in names
        assert all(prompt.name.startswith("skill_") for prompt in prompts)
        assert all(str(resource.uri).startswith("skill://") for resource in resources)
        return names, len(prompts), len(resources)

    names, prompt_count, resource_count = asyncio.run(inspect())

    status = asyncio.run(system_status())
    assert status["status"] == "ok"
    assert status["version"] == __version__
    assert status["database"]["ready"] is True
    assert status["database"]["schema_version"] == 4
    assert status["database"]["path"] == "core.db"
    assert status["counts"]["tools"] == len(names)
    assert status["counts"]["prompts"] == prompt_count
    assert status["counts"]["resources"] == resource_count
    assert str(Path.home()) not in json.dumps(status)


def test_health_mcp_initialize_and_api_absence() -> None:
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "foundation-test", "version": "1.0"},
        },
    }

    with TestClient(app) as client:
        health = client.get("/health")
        api = client.get("/api")
        todos = client.get("/api/todos")
        jira = client.get("/api/jira")
        initialize = client.post(
            "/mcp",
            json=initialize_request,
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert health.status_code == 200
    body = health.json()
    assert body["database"]["ready"] is True
    assert body["database"]["schema_version"] == 4
    assert "token" not in health.text.lower()
    assert "password" not in health.text.lower()
    assert str(Path.home()) not in health.text
    assert api.status_code == 404
    assert todos.status_code == 404
    assert jira.status_code == 404
    assert initialize.status_code == 200
    data_line = next(
        line.removeprefix("data: ")
        for line in initialize.text.splitlines()
        if line.startswith("data: ")
    )
    assert json.loads(data_line)["result"]["serverInfo"]["name"] == "sb"
