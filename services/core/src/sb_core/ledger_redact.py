"""Deterministic, code-owned redaction for ledger entries.

Never rejects content — always returns a scrubbed string plus a changed flag.
Rule order is specific-first, generic-last so a narrow pattern (e.g. an AWS
access key) is redacted before broader patterns (e.g. a generic long hex
string) could otherwise double-match or mis-tag it.
"""

from __future__ import annotations

import re
from typing import Optional

REDACTION_RULES_VERSION = 1

# Each rule: (kind, compiled pattern, replacement template or callable).
# Replacement receives the match and returns the substituted text.

_AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

_AWS_SECRET_RE = re.compile(
    r"(?i)((?:aws_)?secret[_-]?access[_-]?key\s*[:=]\s*)([A-Za-z0-9/+]{40})"
)

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*")

_JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)

_BASIC_AUTH_URL_RE = re.compile(r"(https?://)[^:@\s/]+:[^@\s/]+@")

_ENV_SECRET_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL)[A-Z0-9_]*)\s*=\s*[^\s]+"
)

_LANGSMITH_KEY_RE = re.compile(r"\bls__[A-Za-z0-9]{20,}\b")

# Generic long hex, but only when a secret-ish keyword appears within 20 chars
# before it (so commit SHAs etc. are left alone).
_GENERIC_LONG_HEX_RE = re.compile(
    r"(?i)(?:secret|password|token|key).{0,20}?\b([a-f0-9]{40,})\b"
)


def _redact_aws_key(text: str) -> tuple[str, bool]:
    new_text, n = _AWS_KEY_RE.subn("[REDACTED:AWS_KEY]", text)
    return new_text, n > 0


def _redact_aws_secret(text: str) -> tuple[str, bool]:
    def _sub(m: re.Match) -> str:
        return f"{m.group(1)}[REDACTED:AWS_SECRET]"

    new_text, n = _AWS_SECRET_RE.subn(_sub, text)
    return new_text, n > 0


def _redact_bearer(text: str) -> tuple[str, bool]:
    new_text, n = _BEARER_RE.subn("Bearer [REDACTED:BEARER]", text)
    return new_text, n > 0


def _redact_jwt(text: str) -> tuple[str, bool]:
    new_text, n = _JWT_RE.subn("[REDACTED:JWT]", text)
    return new_text, n > 0


def _redact_basic_auth_url(text: str) -> tuple[str, bool]:
    new_text, n = _BASIC_AUTH_URL_RE.subn(r"\1[REDACTED:BASIC_AUTH]@", text)
    return new_text, n > 0


def _redact_env_secret(text: str) -> tuple[str, bool]:
    def _sub(m: re.Match) -> str:
        return f"{m.group(1)}=[REDACTED:ENV]"

    new_text, n = _ENV_SECRET_RE.subn(_sub, text)
    return new_text, n > 0


def _redact_langsmith_key(text: str) -> tuple[str, bool]:
    new_text, n = _LANGSMITH_KEY_RE.subn("[REDACTED:LANGSMITH_KEY]", text)
    return new_text, n > 0


def _redact_generic_long_hex(text: str) -> tuple[str, bool]:
    changed = False

    def _sub(m: re.Match) -> str:
        nonlocal changed
        changed = True
        full = m.group(0)
        hex_value = m.group(1)
        return full.replace(hex_value, "[REDACTED:GENERIC_LONG_HEX]")

    new_text = _GENERIC_LONG_HEX_RE.sub(_sub, text)
    return new_text, changed


# Order matters: specific patterns before generic ones.
_RULES = [
    _redact_aws_key,
    _redact_aws_secret,
    _redact_bearer,
    _redact_jwt,
    _redact_basic_auth_url,
    _redact_env_secret,
    _redact_langsmith_key,
    _redact_generic_long_hex,
]


def redact(text: str) -> tuple[str, bool]:
    """Apply all redaction rules in order. Deterministic. Never raises."""
    if not text:
        return text, False
    result = text
    changed = False
    for rule in _RULES:
        result, rule_changed = rule(result)
        changed = changed or rule_changed
    return result, changed


def redact_entry(
    *,
    summary: str,
    body: Optional[str],
    refs: Optional[list[dict]],
) -> tuple[str, Optional[str], list[dict], bool]:
    """Scrub summary, body, and ref values/urls. Returns the scrubbed triple
    plus a combined ``was_changed`` flag."""
    scrubbed_summary, summary_changed = redact(summary)

    scrubbed_body: Optional[str] = None
    body_changed = False
    if body is not None:
        scrubbed_body, body_changed = redact(body)

    scrubbed_refs: list[dict] = []
    refs_changed = False
    for ref in refs or []:
        if not isinstance(ref, dict):
            scrubbed_refs.append(ref)
            continue
        new_ref = dict(ref)
        for field in ("value", "url", "label"):
            if isinstance(new_ref.get(field), str):
                new_val, field_changed = redact(new_ref[field])
                new_ref[field] = new_val
                refs_changed = refs_changed or field_changed
        scrubbed_refs.append(new_ref)

    was_changed = summary_changed or body_changed or refs_changed
    return scrubbed_summary, scrubbed_body, scrubbed_refs, was_changed
