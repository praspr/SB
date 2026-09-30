"""Tests for identity / rich-roots / goals-path configuration."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_yaml_identity_is_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(
        yaml_path,
        "identity:\n  name: Jane Dev\n  email: jane@example.com\n",
    )
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()
    assert s.identity_name == "Jane Dev"
    assert s.identity_email == "jane@example.com"


def test_identity_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", "/nonexistent/x.yaml")
    from sb_core.config import Settings

    s = Settings()
    assert s.identity_name is None
    assert s.identity_email is None


def test_identity_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_CORE_IDENTITY_NAME", "Env Name")
    from sb_core.config import Settings

    s = Settings()
    assert s.identity_name == "Env Name"


def test_identity_emails_list_selects_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(
        yaml_path,
        "identity:\n"
        "  name: Multi Mailbox\n"
        "  emails:\n"
        "    - first@example.com\n"
        "    - second@example.com\n",
    )
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()
    assert s.identity_email == "first@example.com"


def test_identity_email_takes_precedence_over_emails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(
        yaml_path,
        "identity:\n"
        "  email: primary@example.com\n"
        "  emails:\n"
        "    - other@example.com\n",
    )
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()
    assert s.identity_email == "primary@example.com"


def test_rich_roots_preserve_label_and_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(
        yaml_path,
        "roots:\n"
        "  - path: /work/a\n"
        "    label: Primary\n"
        "    domain: work\n"
        "  - /work/b\n",
    )
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", str(yaml_path))
    from sb_core.config import Settings

    s = Settings()
    # Plain path list stays backward compatible
    assert s.roots == ["/work/a", "/work/b"]
    # Detailed roots preserve label + domain
    assert s.roots_detailed[0] == {
        "path": "/work/a",
        "label": "Primary",
        "domain": "work",
    }
    assert s.roots_detailed[1] == {"path": "/work/b"}


def test_goals_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SB_CORE_GOALS_PATH", raising=False)
    monkeypatch.setenv("SB_CORE_CONFIG_PATH", "/nonexistent/x.yaml")
    from sb_core.config import Settings

    s = Settings()
    assert str(s.goals_path).endswith("goals.yaml")


def test_goals_path_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_CORE_GOALS_PATH", "/custom/goals.yaml")
    from sb_core.config import Settings

    s = Settings()
    assert s.goals_path == Path("/custom/goals.yaml")


def test_llm_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SB_CORE_LLM_BASE_URL", raising=False)
    from sb_core.config import Settings

    s = Settings()
    assert s.llm_base_url == "http://127.0.0.1:9999"
    assert s.llm_timeout > 0
