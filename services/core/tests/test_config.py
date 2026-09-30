"""Tests for configuration: YAML loading, env overrides, list parsing robustness."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _fresh_settings(
    monkeypatch: pytest.MonkeyPatch, **env_overrides
) -> "Settings":  # noqa: F821
    """Import a fresh Settings instance with the given env vars.

    We can't reload the module-level singleton; instead instantiate directly.
    """
    # Apply env overrides
    for k, v in env_overrides.items():
        monkeypatch.setenv(k, v)
    # Remove vars not in overrides so tests start clean
    from sb_core.config import Settings

    return Settings()


# ---------------------------------------------------------------------------
# Issue 4a: YAML config loading
# ---------------------------------------------------------------------------


def test_yaml_config_loads_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, "roots:\n  - /workspace/a\n  - /workspace/b\n")

    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()

    assert s.roots == ["/workspace/a", "/workspace/b"]


def test_yaml_config_loads_git_authors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(
        yaml_path, 'git_authors:\n  - "alice@example.com"\n  - "bob@example.com"\n'
    )

    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()

    assert "alice@example.com" in s.git_authors
    assert "bob@example.com" in s.git_authors


def test_env_overrides_yaml_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment variables must take priority over YAML values."""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, "roots:\n  - /from/yaml\n")

    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    monkeypatch.setenv("SB_CORE_ROOTS", '["/from/env"]')

    from sb_core.config import Settings

    s = Settings()

    assert s.roots == ["/from/env"]


def test_missing_yaml_is_silently_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """A nonexistent YAML config path must not crash Settings()."""
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", "/nonexistent/path/config.yaml")

    from sb_core.config import Settings

    s = Settings()  # must not raise

    assert s.roots == []


# ---------------------------------------------------------------------------
# Issue 4b: Robust list parsing from env
# ---------------------------------------------------------------------------


def test_list_from_env_json_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_CORE_ROOTS", '["/a", "/b"]')
    from sb_core.config import Settings

    s = Settings()
    assert s.roots == ["/a", "/b"]


def test_list_from_env_space_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Space-separated values must be accepted without crashing."""
    monkeypatch.setenv("SB_CORE_ROOTS", "/a /b /c")
    from sb_core.config import Settings

    s = Settings()
    assert s.roots == ["/a", "/b", "/c"]


def test_list_from_env_single_value_no_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_CORE_ROOTS", "/single/path")
    from sb_core.config import Settings

    s = Settings()
    assert s.roots == ["/single/path"]


def test_list_from_env_empty_string_gives_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SB_CORE_ROOTS", "")
    from sb_core.config import Settings

    s = Settings()
    assert s.roots == []


def test_list_from_env_malformed_json_falls_back_to_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON (e.g., unclosed bracket) must not crash; parse as space-split."""
    monkeypatch.setenv("SB_CORE_ROOTS", "[broken")
    from sb_core.config import Settings

    # Must not raise; actual value depends on fallback strategy
    s = Settings()
    assert isinstance(s.roots, list)


# ---------------------------------------------------------------------------
# Issue 4c: SB_CORE_CONFIG_PATH overrides default YAML path
# ---------------------------------------------------------------------------


def test_config_path_env_points_to_custom_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_yaml = tmp_path / "custom.yaml"
    _write_yaml(custom_yaml, "roots:\n  - /custom/root\n")

    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(custom_yaml))
    from sb_core.config import Settings

    s = Settings()

    assert "/custom/root" in s.roots
