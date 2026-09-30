"""Tests for the claudegate LLM client with SHA-256 content cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

import sb_core.llm as llm


def _configure(monkeypatch: pytest.MonkeyPatch, cache_dir: Path) -> None:
    monkeypatch.setattr(llm, "_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(llm, "_base_url", lambda: "http://127.0.0.1:9999")
    monkeypatch.setattr(llm, "_timeout", lambda: 5.0)
    monkeypatch.setattr(llm, "_model", lambda: "test-model")
    monkeypatch.setattr(llm, "_tier", lambda: None)


def test_cache_key_includes_model_tier_and_max_tokens() -> None:
    key = llm.cache_key("m", "hello", tier=None, max_tokens=1024)
    expected = hashlib.sha256(b"m\nNone\n1024\nhello").hexdigest()
    assert key == expected
    # tier changes the key
    assert llm.cache_key("m", "hello", tier="fast", max_tokens=1024) != key
    # max_tokens changes the key
    assert llm.cache_key("m", "hello", tier=None, max_tokens=2048) != key


def test_completion_is_cached_after_first_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)
    calls = {"n": 0}

    def fake_post(url, payload, timeout):
        calls["n"] += 1
        return {"choices": [{"message": {"content": "generated text"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)

    out1 = llm.complete("prompt A")
    assert out1 == "generated text"
    assert calls["n"] == 1

    def boom(url, payload, timeout):  # pragma: no cover - must not run
        raise AssertionError("cache miss: HTTP should not be called")

    monkeypatch.setattr(llm, "_http_post", boom)
    out2 = llm.complete("prompt A")
    assert out2 == "generated text"


def test_precached_response_avoids_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)
    key = llm.cache_key(
        "test-model", "prewritten", tier=None, max_tokens=llm._MAX_TOKENS
    )
    (tmp_path / f"{key}.txt").write_text("from cache", encoding="utf-8")

    def boom(url, payload, timeout):  # pragma: no cover
        raise AssertionError("should not hit HTTP")

    monkeypatch.setattr(llm, "_http_post", boom)
    assert llm.complete("prewritten") == "from cache"


def test_unavailable_backend_raises_llm_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)

    def fail(url, payload, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(llm, "_http_post", fail)

    with pytest.raises(llm.LLMUnavailable):
        llm.complete("prompt")


def test_no_cache_written_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)

    def fail(url, payload, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(llm, "_http_post", fail)
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("prompt")
    assert list(tmp_path.glob("*.txt")) == []


# ---------------------------------------------------------------------------
# Item 9: cache corruption / empty / atomic write / bounded bytes
# ---------------------------------------------------------------------------


def test_corrupt_cache_is_treated_as_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)
    key = llm.cache_key("test-model", "p", tier=None, max_tokens=llm._MAX_TOKENS)
    # Write invalid (non-UTF-8) bytes to the cache file.
    (tmp_path / f"{key}.txt").write_bytes(b"\xff\xfe\x00bad")

    monkeypatch.setattr(
        llm, "_http_post", lambda url, payload, timeout: {"content": "fresh"}
    )
    assert llm.complete("p") == "fresh"


def test_empty_cache_file_is_a_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)
    key = llm.cache_key("test-model", "p", tier=None, max_tokens=llm._MAX_TOKENS)
    (tmp_path / f"{key}.txt").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        llm, "_http_post", lambda url, payload, timeout: {"content": "fresh"}
    )
    assert llm.complete("p") == "fresh"


def test_cache_write_is_atomic_no_temp_left_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        llm, "_http_post", lambda url, payload, timeout: {"content": "value"}
    )
    llm.complete("p")
    # Only the final .txt file remains; no partial temp files.
    files = sorted(f.name for f in tmp_path.iterdir())
    assert all(f.endswith(".txt") for f in files)
    assert len(files) == 1


def test_response_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, tmp_path)
    huge = "x" * (llm._MAX_RESPONSE_CHARS + 5000)
    monkeypatch.setattr(
        llm, "_http_post", lambda url, payload, timeout: {"content": huge}
    )
    out = llm.complete("p")
    assert len(out) <= llm._MAX_RESPONSE_CHARS
