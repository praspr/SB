"""Adapter: scan CHANGELOG.md files in configured roots for version headings.

Safe, bounded, and read-only.  raw_ref is ``path:line`` for source tracing.
``occurred_at`` is extracted from the heading date (``## [1.2.0] - 2026-09-01``)
and normalised to canonical UTC via ``normalize_occurred_at``.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

from ..store.signals import normalize_occurred_at, upsert_signal

logger = logging.getLogger(__name__)

# Match version headings with optional date: ## [1.2.0], ## v1.2.0, ## 1.2.0
_VERSION_RE = re.compile(
    r"^#{1,3}\s+"  # leading hashes
    r"(?:\[?)v?(\d+\.\d+[\d.]*(?:[-+][^\]]*)?)\]?"  # version number
    r"(?:\s*[-–]\s*(\d{4}-\d{2}-\d{2}))?",  # optional " - YYYY-MM-DD"
    re.IGNORECASE,
)

# Max bytes read per CHANGELOG.md (256 KiB) – safety bound
_MAX_FILE_BYTES = 256 * 1024


def run(core_conn: sqlite3.Connection, *, roots: list[Path]) -> int:
    """Scan each root for CHANGELOG.md and upsert version-entry signals."""
    total = 0
    for root in roots:
        changelog = Path(root) / "CHANGELOG.md"
        if not changelog.exists():
            continue
        try:
            total += _process(core_conn, changelog)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "changelog adapter: failed to process %s: %s", changelog, exc
            )
    return total


def _process(core_conn: sqlite3.Connection, path: Path) -> int:
    raw = path.read_bytes()[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")
    lines = raw.splitlines()

    count = 0
    current_heading: str | None = None
    current_lineno: int = 0
    current_date: str = ""
    body_lines: list[str] = []

    def _flush() -> None:
        nonlocal count
        if current_heading is None:
            return
        body = "\n".join(body_lines).strip()
        source_id = f"{path}:{current_lineno}:{current_heading}"
        upsert_signal(
            core_conn,
            source="changelog",
            source_id=source_id,
            kind="release",
            occurred_at=normalize_occurred_at(current_date),
            title=current_heading,
            body=body[:2000] if body else None,
            raw_ref=f"{path}:{current_lineno}",
        )
        count += 1

    for lineno, line in enumerate(lines, start=1):
        m = _VERSION_RE.match(line.strip())
        if m:
            _flush()
            current_heading = line.strip()
            current_lineno = lineno
            current_date = m.group(2) or ""  # may be empty for headings without date
            body_lines = []
        elif current_heading is not None:
            body_lines.append(line)

    _flush()
    return count
