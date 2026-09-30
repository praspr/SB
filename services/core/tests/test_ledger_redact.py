"""Per-rule fixture tests for sb_core.ledger_redact.

One positive (redacts) and one negative (no-op) fixture per rule, plus
integration tests for redact_entry() across summary/body/refs.
"""

from __future__ import annotations

from sb_core.ledger_redact import REDACTION_RULES_VERSION, redact, redact_entry


def test_rules_version_is_stamped() -> None:
    assert REDACTION_RULES_VERSION == 1


# ---------------------------------------------------------------------------
# AWS_KEY
# ---------------------------------------------------------------------------


def test_aws_key_is_redacted() -> None:
    text = "found key AKIAABCDEFGHIJKLMNOP in the log"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "AKIAABCDEFGHIJKLMNOP" not in scrubbed
    assert "[REDACTED:AWS_KEY]" in scrubbed


def test_aws_key_no_op_on_unrelated_text() -> None:
    text = "no secrets here, just AKIA is too short"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# AWS_SECRET
# ---------------------------------------------------------------------------


def test_aws_secret_is_redacted() -> None:
    text = "aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY12"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "wJalrXUtnFEMI" not in scrubbed
    assert "[REDACTED:AWS_SECRET]" in scrubbed


def test_aws_secret_no_op_when_value_too_short() -> None:
    text = "secret_access_key: short"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# BEARER
# ---------------------------------------------------------------------------


def test_bearer_token_is_redacted() -> None:
    text = "curl -H 'Authorization: Bearer abcDEF123-_.~+/=='"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "abcDEF123" not in scrubbed
    assert "Bearer [REDACTED:BEARER]" in scrubbed


def test_bearer_no_op_without_bearer_keyword() -> None:
    text = "no auth header here"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def test_jwt_is_redacted() -> None:
    text = (
        "token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpM"
    )
    scrubbed, changed = redact(text)
    assert changed is True
    assert "eyJhbGciOiJIUzI1NiJ9" not in scrubbed
    assert "[REDACTED:JWT]" in scrubbed


def test_jwt_no_op_on_two_segment_value() -> None:
    text = "eyJhbGciOiJIUzI1NiJ9.notavalidjwt"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# BASIC_AUTH_URL
# ---------------------------------------------------------------------------


def test_basic_auth_url_is_redacted() -> None:
    text = "cloning https://user:hunter2@example.com/repo.git"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "hunter2" not in scrubbed
    assert "https://[REDACTED:BASIC_AUTH]@example.com/repo.git" in scrubbed


def test_basic_auth_url_no_op_on_plain_url() -> None:
    text = "see https://example.com/repo.git for details"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# ENV_SECRET
# ---------------------------------------------------------------------------


def test_env_secret_is_redacted() -> None:
    text = "export DB_PASSWORD=hunter2secret"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "hunter2secret" not in scrubbed
    assert "DB_PASSWORD=[REDACTED:ENV]" in scrubbed


def test_env_secret_no_op_on_unrelated_assignment() -> None:
    text = "export LOG_LEVEL=debug"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# LANGSMITH_KEY
# ---------------------------------------------------------------------------


def test_langsmith_key_is_redacted() -> None:
    text = "set LANGCHAIN_API_KEY manually: ls__abcdefghijklmnopqrstuvwx"
    scrubbed, changed = redact(text)
    assert changed is True
    assert "[REDACTED:LANGSMITH_KEY]" in scrubbed


def test_langsmith_key_no_op_when_too_short() -> None:
    text = "ls__short"
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# GENERIC_LONG_HEX
# ---------------------------------------------------------------------------


def test_generic_long_hex_is_redacted_near_secret_keyword() -> None:
    text = "token: " + "a" * 40
    scrubbed, changed = redact(text)
    assert changed is True
    assert "[REDACTED:GENERIC_LONG_HEX]" in scrubbed
    assert "a" * 40 not in scrubbed


def test_generic_long_hex_no_op_for_bare_commit_sha() -> None:
    text = "fixed in commit " + "f" * 40
    scrubbed, changed = redact(text)
    assert changed is False
    assert scrubbed == text


# ---------------------------------------------------------------------------
# redact_entry integration
# ---------------------------------------------------------------------------


def test_redact_entry_scrubs_summary_body_and_refs() -> None:
    summary, body, refs, changed = redact_entry(
        summary="Rotated AKIAABCDEFGHIJKLMNOP",
        body="Bearer abcDEF123.token",
        refs=[{"kind": "note", "value": "password=hunter2secretvalue", "url": "https://user:hunter2@example.com"}],
    )
    assert changed is True
    assert "AKIA" not in summary
    assert "Bearer [REDACTED:BEARER]" in body
    assert "[REDACTED:BASIC_AUTH]" in refs[0]["url"]


def test_redact_entry_no_op_on_clean_input() -> None:
    summary, body, refs, changed = redact_entry(
        summary="Shipped the ledger foundation",
        body="No secrets in here.",
        refs=[{"kind": "pr", "value": "45", "url": "https://example.com/pr/45"}],
    )
    assert changed is False
    assert summary == "Shipped the ledger foundation"
    assert body == "No secrets in here."
    assert refs[0]["url"] == "https://example.com/pr/45"


def test_redact_entry_handles_none_body_and_refs() -> None:
    summary, body, refs, changed = redact_entry(summary="No body here", body=None, refs=None)
    assert body is None
    assert refs == []
    assert changed is False
