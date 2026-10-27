"""L4: config-driven seed projects and known-email overrides (sb-jira)."""

from __future__ import annotations

from sb_jira import file_store as fs
from sb_jira.config import Settings


def test_default_known_email_mapping_is_preserved() -> None:
    assert fs._guess_email("PRASAD P R") == "praspr@cisco.com"


def test_email_fallback_uses_default_domain() -> None:
    assert fs._guess_email("Jane Doe") == "jane.doe@cisco.com"


def test_known_emails_override_takes_effect(monkeypatch) -> None:
    custom = Settings(known_emails={"Ada Lovelace": "ada@example.com"})
    monkeypatch.setattr(fs, "settings", custom)
    assert fs._guess_email("Ada Lovelace") == "ada@example.com"


def test_fallback_domain_override_takes_effect(monkeypatch) -> None:
    custom = Settings(email_fallback_domain="example.org")
    monkeypatch.setattr(fs, "settings", custom)
    assert fs._guess_email("Jane Doe") == "jane.doe@example.org"
