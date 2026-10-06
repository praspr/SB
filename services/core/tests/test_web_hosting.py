"""Tests for /_ui SPA hosting and /proxy/* passthrough routes."""

from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from sb_core import cursor_auth
from sb_core.config import settings
from sb_core.main import app


# ---------------------------------------------------------------------------
# /_ui SPA hosting
# ---------------------------------------------------------------------------


@pytest.fixture
def dist_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<html><body>index</body></html>")
    (d / "assets" / "app.js").write_bytes(b"console.log('hi')")
    return d


def test_ui_unknown_subpath_falls_back_to_index(dist_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "web_dist_path", dist_dir)
    with TestClient(app) as client:
        resp = client.get("/_ui/some/deep/route")
    assert resp.status_code == 200
    assert b"index" in resp.content


def test_ui_real_asset_served(dist_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "web_dist_path", dist_dir)
    with TestClient(app) as client:
        resp = client.get("/_ui/assets/app.js")
    assert resp.status_code == 200
    assert resp.content == b"console.log('hi')"


def test_ui_missing_dist_returns_503(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "web_dist_path", tmp_path / "nonexistent")
    with TestClient(app) as client:
        resp = client.get("/_ui/")
    assert resp.status_code == 503
    assert "not built" in resp.text


def test_ui_root_redirects(dist_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "web_dist_path", dist_dir)
    with TestClient(app) as client:
        resp = client.get("/_ui", follow_redirects=False)
    assert resp.status_code in (307, 308)
    assert resp.headers["location"].endswith("/_ui/")


# ---------------------------------------------------------------------------
# /proxy/claudegate
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes, content_type: str = "application/json") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


def test_claudegate_proxy_forwards_and_returns_body(monkeypatch) -> None:
    captured = {}

    class _FakeClient:
        def __init__(self, *a, **kw) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            return _FakeResponse(200, b'{"ok": true}')

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    with TestClient(app) as client:
        resp = client.get("/proxy/claudegate/api/status")

    assert resp.status_code == 200
    assert resp.content == b'{"ok": true}'
    assert captured["url"] == "http://localhost:9999/api/status"


def test_claudegate_proxy_upstream_down_returns_502(monkeypatch) -> None:
    class _FakeClient:
        def __init__(self, *a, **kw) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None, headers=None):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    with TestClient(app) as client:
        resp = client.get("/proxy/claudegate/api/status")

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /proxy/cursor + cursor_auth
# ---------------------------------------------------------------------------


def _make_fake_jwt(sub: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.signature"


def _write_fake_cursor_db(path: Path, token: str) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    conn.execute(
        "INSERT INTO ItemTable (key, value) VALUES ('cursorAuth/accessToken', ?)",
        (token,),
    )
    conn.commit()
    conn.close()


def test_get_cursor_cookie_from_fake_db(tmp_path: Path) -> None:
    db_path = tmp_path / "state.vscdb"
    token = _make_fake_jwt("auth0|USER123")
    _write_fake_cursor_db(db_path, token)

    cookie = cursor_auth.get_cursor_cookie(db_path=db_path, use_cache=False)

    assert cookie is not None
    assert cookie.startswith("WorkosCursorSessionToken=")
    assert "USER123" in cookie


def test_get_cursor_cookie_missing_db_returns_none(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.vscdb"
    cookie = cursor_auth.get_cursor_cookie(db_path=missing, use_cache=False)
    assert cookie is None


def test_cursor_proxy_forwards_with_mocked_cookie(monkeypatch) -> None:
    monkeypatch.setattr("sb_core.main.get_cursor_cookie", lambda: "WorkosCursorSessionToken=abc")

    captured = {}

    class _FakeClient:
        def __init__(self, *a, **kw) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return _FakeResponse(200, b'{"usage": 1}')

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    with TestClient(app) as client:
        resp = client.get("/proxy/cursor/api/usage-summary")

    assert resp.status_code == 200
    assert resp.content == b'{"usage": 1}'
    assert captured["url"] == "https://cursor.com/api/usage-summary"
    assert captured["headers"]["Cookie"] == "WorkosCursorSessionToken=abc"
