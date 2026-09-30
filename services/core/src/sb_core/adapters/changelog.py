"""Adapter: scan CHANGELOG.md files in configured roots for version headings.

Safe, bounded, and read-only.  raw_ref is ``path:line`` for source tracing.
``occurred_at`` is extracted from the heading date (``## [1.2.0] - 2026-09-01``)
and normalised to canonical UTC via ``normalize_occurred_at``.

In addition to the version-heading signal upsert, any project enrolled in
``sb_project_registry`` gets its dated (``## [YYYY-MM-DD]``) narrative
bullets promoted into ``sb_ledger`` via ``_promote_to_ledger``. This lets an
existing ``sync_adapters`` run pick up ledger entries that were appended to
CHANGELOG.md by a means other than ``ledger_log`` (e.g. hand-edited), the
same way ``sync_ledger_from_files`` does, without requiring a separate call.
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
    """Scan each root for CHANGELOG.md, upsert version-entry signals, and
    (for roots matching a registered ledger project) promote narrative
    bullets into ``sb_ledger``. Returns the version-entry signal count only,
    to preserve the existing return contract used by the adapter dispatcher.
    """
    total = 0
    registry_by_root = _registry_by_root(core_conn)
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
        try:
            _promote_to_ledger(core_conn, changelog, root, registry_by_root)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "changelog adapter: failed to promote ledger entries for %s: %s",
                changelog,
                exc,
            )
    return total


def _registry_by_root(core_conn: sqlite3.Connection) -> dict[str, str]:
    """Map resolved root path -> project name, from sb_project_registry.

    Best-effort: returns an empty map if the table does not exist yet (an
    older core.db that has not run the ledger migration) or the query fails
    for any other reason.
    """
    try:
        rows = core_conn.execute(
            "SELECT project, root_path FROM sb_project_registry"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    mapping: dict[str, str] = {}
    for row in rows:
        try:
            resolved = str(Path(row["root_path"]).expanduser().resolve())
        except OSError:
            continue
        mapping[resolved] = row["project"]
    return mapping


def _promote_to_ledger(
    core_conn: sqlite3.Connection,
    changelog: Path,
    root: Path,
    registry_by_root: dict[str, str],
) -> int:
    """Promote dated narrative bullets from *changelog* into ``sb_ledger``,
    only when *root* matches a project in ``sb_project_registry``.

    Idempotent via ``content_sha256`` (see ``store.ledger.append_ledger``).
    Never writes to the file. Returns the number of newly-promoted rows.
    """
    try:
        resolved_root = str(Path(root).expanduser().resolve())
    except OSError:
        return 0
    project = registry_by_root.get(resolved_root)
    if project is None:
        return 0

    from ..ledger_session import derive_session_id, ensure_session_row
    from ..ledger_sync import _iter_dated_bullets
    from ..store.ledger import append_ledger

    text = changelog.read_bytes()[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")

    session_id = derive_session_id(agent="adapter", project=project, working_dir=str(root))
    ensure_session_row(
        core_conn,
        session_id,
        agent="adapter",
        project=project,
        working_dir=str(root),
        extras=None,
    )

    promoted = 0
    for date_str, bullet in _iter_dated_bullets(text):
        time_part = bullet["time"] or "00:00:00"
        ts = f"{date_str}T{time_part}Z"
        result = append_ledger(
            core_conn,
            project=project,
            summary=bullet["summary"],
            action_verb=bullet["verb"],
            scope=bullet["scope"],
            refs=bullet["refs"],
            session_id=session_id,
            agent="adapter",
            working_dir=str(root),
            source_harness="changelog-adapter",
            origin="adapter-promote",
            ts=ts,
        )
        if result["was_new"]:
            promoted += 1
    return promoted


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
