"""Adapter: emit commit signals from git log.

Uses structured subprocess args (no shell=True), bounded timeout.
Author filtering is optional.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional

from ..store.signals import upsert_signal

logger = logging.getLogger(__name__)

# git pretty-format fields separated by ASCII unit separator
_FIELD_SEP = "\x1f"
# records separated by ASCII record separator
_RECORD_SEP = "\x1e"
_GIT_FORMAT = f"%H{_FIELD_SEP}%aI{_FIELD_SEP}%s{_FIELD_SEP}%ae"


def run(
    core_conn: sqlite3.Connection,
    *,
    roots: list[Path],
    since_days: int = 30,
    authors: Optional[list[str]] = None,
    timeout: float = 15.0,
) -> int:
    """Emit one 'commit' signal per git commit across all roots."""
    total = 0
    for root in roots:
        root = Path(root)
        if not (root / ".git").exists():
            continue
        try:
            total += _git_root(
                core_conn,
                root,
                since_days=since_days,
                authors=authors,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("git adapter: failed for %s: %s", root, exc)
    return total


def _git_root(
    core_conn: sqlite3.Connection,
    root: Path,
    *,
    since_days: int,
    authors: Optional[list[str]],
    timeout: float,
) -> int:
    cmd: list[str] = [
        "git",
        "-C",
        str(root),
        "log",
        f"--since={since_days} days ago",
        f"--format={_GIT_FORMAT}{_RECORD_SEP}",
    ]
    if authors:
        for author in authors:
            cmd += ["--author", author]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("git adapter: git log timed out for %s", root)
        return 0

    if result.returncode != 0:
        logger.warning(
            "git adapter: git log failed for %s: %s", root, result.stderr.strip()
        )
        return 0

    count = 0
    for record in result.stdout.split(_RECORD_SEP):
        record = record.strip()
        if not record:
            continue
        parts = record.split(_FIELD_SEP, 3)
        if len(parts) < 3:
            continue
        sha = parts[0].strip()
        occurred_at = parts[1].strip() if len(parts) > 1 else ""
        subject = parts[2].strip() if len(parts) > 2 else "(no subject)"
        # author_email might be missing for malformed records
        upsert_signal(
            core_conn,
            source="git",
            source_id=sha,
            kind="commit",
            occurred_at=occurred_at,
            title=subject,
            scope=root.name,
            verb="committed",
            refs=[],
            raw_ref=f"{root}:{sha[:12]}",
        )
        count += 1
    return count
