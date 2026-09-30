"""Dual-write sync between ``sb_ledger`` rows and per-project CHANGELOG.md files.

- ``format_bullet`` renders one ledger row as a single markdown bullet line.
- ``append_to_changelog`` writes that bullet into the correct dated section
  of a CHANGELOG.md, creating the section if needed, and never touches any
  other byte of the file.
- ``sync_from_files`` is the read direction: it hydrates ``sb_ledger`` from
  bullets already present in enrolled projects' CHANGELOG.md files. It never
  writes to those files.
"""

from __future__ import annotations

import fcntl
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_DATE_HEADING_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*$")
_UNRELEASED_RE = re.compile(r"^## Unreleased\s*$", re.IGNORECASE)
_TITLE_RE = re.compile(r"^# ")

# Bullet formats we can parse back out of a CHANGELOG.md during hydration:
#   - **14:32:07 UTC** · **Debugged** summary … — *`scope`*
#   - **Debugged** summary … — *`scope`*      (legacy, no timestamp)
_TIMED_BULLET_RE = re.compile(
    r"^- \*\*(?P<time>\d{2}:\d{2}:\d{2}) UTC\*\* · \*\*(?P<verb>[A-Za-z][A-Za-z ]*)\*\* (?P<rest>.*)$"
)
_LEGACY_BULLET_RE = re.compile(
    r"^- \*\*(?P<verb>[A-Za-z][A-Za-z ]*)\*\* (?P<rest>.*)$"
)
_SCOPE_SUFFIX_RE = re.compile(r"\s*—\s*\*`(?P<scope>[^`]+)`\*\s*$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_CODE_REF_RE = re.compile(r"`([^`]+)`")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_refs(refs: list[dict]) -> str:
    parts: list[str] = []
    for ref in refs or []:
        if not isinstance(ref, dict):
            continue
        label = ref.get("label") or ref.get("value") or ""
        url = ref.get("url")
        if not label:
            continue
        if url:
            parts.append(f"[{label}]({url})")
        else:
            parts.append(f"`{label}`")
    return ", ".join(parts)


def format_bullet(row: dict) -> str:
    """Render one ledger row as a single CHANGELOG.md bullet line.

    ``- **HH:MM:SS UTC** · **Verb** Summary [links…] — *`scope`*``

    Refs with a ``url`` render as inline markdown links (using ``label`` or
    ``value`` as the link text); refs without a url render as inline code.
    The trailing scope suffix is omitted when the row has no scope.
    """
    ts = row.get("ts") or ""
    time_part = ts[11:19] if len(ts) >= 19 else datetime.now(timezone.utc).strftime("%H:%M:%S")
    verb = row.get("action_verb") or "Note"
    summary = (row.get("summary") or "").strip()

    refs_text = _render_refs(row.get("refs") or [])
    line = f"- **{time_part} UTC** · **{verb}** {summary}"
    if refs_text:
        line = f"{line} {refs_text}"
    scope = row.get("scope")
    if scope:
        line = f"{line} — *`{scope}`*"
    return line


# ---------------------------------------------------------------------------
# File locking
# ---------------------------------------------------------------------------


@contextmanager
def _locked(changelog_path: Path) -> Iterator[None]:
    lock_path = changelog_path.with_name(changelog_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(lock_path, "a+")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
        fd.close()


# ---------------------------------------------------------------------------
# Write direction: append_to_changelog
# ---------------------------------------------------------------------------


def _today_heading(row: dict) -> str:
    ts = row.get("ts") or ""
    date_str = ts[:10] if len(ts) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"## [{date_str}]"


def append_to_changelog(changelog_path: Path, row: dict) -> None:
    """Append *row* as a bullet under today's dated heading in *changelog_path*.

    Creates the file (with a ``# Changelog`` title) if it does not exist.
    Ensures today's ``## [YYYY-MM-DD]`` heading exists, creating it directly
    below ``## Unreleased`` when that convention is used, or above the most
    recent existing dated heading otherwise (or at the top, under the title,
    when there are no dated headings yet). The new bullet is inserted as the
    *first* bullet under today's heading. All other file content is
    preserved byte-for-byte.
    """
    changelog_path = Path(changelog_path)
    heading = _today_heading(row)
    bullet = format_bullet(row)

    with _locked(changelog_path):
        if changelog_path.exists():
            text = changelog_path.read_text(encoding="utf-8")
        else:
            text = "# Changelog\n"

        lines = text.splitlines(keepends=True)
        new_lines = _insert_bullet(lines, heading, bullet)
        changelog_path.parent.mkdir(parents=True, exist_ok=True)
        changelog_path.write_text("".join(new_lines), encoding="utf-8")


def _line_ending(line: str) -> str:
    return "\n" if line.endswith("\n") else ""


def _insert_bullet(lines: list[str], heading: str, bullet: str) -> list[str]:
    heading_line = heading + "\n"
    bullet_line = bullet + "\n"

    # 1. Heading already present: insert bullet as first line after it.
    for i, line in enumerate(lines):
        if line.rstrip("\n") == heading:
            insert_at = i + 1
            return lines[:insert_at] + [bullet_line] + lines[insert_at:]

    # 2. Heading absent: decide where to create it.
    unreleased_idx = None
    first_dated_idx = None
    title_idx = None
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if title_idx is None and _TITLE_RE.match(stripped):
            title_idx = i
        if unreleased_idx is None and _UNRELEASED_RE.match(stripped):
            unreleased_idx = i
        if first_dated_idx is None and _DATE_HEADING_RE.match(stripped):
            first_dated_idx = i

    if unreleased_idx is not None:
        # Insert directly below the Unreleased section: find the next
        # heading (## ...) after it, or end of file, and place the new
        # dated section right before that boundary.
        insert_at = len(lines)
        for i in range(unreleased_idx + 1, len(lines)):
            if lines[i].startswith("## "):
                insert_at = i
                break
        block = ["\n", heading_line, bullet_line, "\n"]
        return lines[:insert_at] + block + lines[insert_at:]

    if first_dated_idx is not None:
        block = [heading_line, bullet_line, "\n"]
        return lines[:first_dated_idx] + block + lines[first_dated_idx:]

    # No Unreleased section, no dated headings: place right after the title
    # (or at the very top if there is no title line).
    insert_at = title_idx + 1 if title_idx is not None else 0
    prefix = lines[:insert_at]
    if prefix and not prefix[-1].endswith("\n\n") and prefix[-1].strip() != "":
        block = ["\n", heading_line, bullet_line, "\n"]
    else:
        block = [heading_line, bullet_line, "\n"]
    return prefix + block + lines[insert_at:]


# ---------------------------------------------------------------------------
# Read direction: sync_from_files (hydration)
# ---------------------------------------------------------------------------


def _parse_refs(rest: str) -> tuple[str, list[dict]]:
    """Best-effort extraction of refs (markdown links + code spans) from the
    bullet body. Returns (summary_without_ref_markup_left_as_is, refs)."""
    refs: list[dict] = []
    for label, url in _MD_LINK_RE.findall(rest):
        refs.append({"kind": "link", "value": label, "url": url, "label": label})
    # Code spans that are not part of a link and not the trailing scope.
    without_scope = _SCOPE_SUFFIX_RE.sub("", rest)
    without_links = _MD_LINK_RE.sub("", without_scope)
    for code in _CODE_REF_RE.findall(without_links):
        refs.append({"kind": "code", "value": code, "label": code})
    return rest, refs


def _parse_bullet(line: str) -> dict | None:
    stripped = line.rstrip("\n")
    m = _TIMED_BULLET_RE.match(stripped)
    has_time = m is not None
    if m is None:
        m = _LEGACY_BULLET_RE.match(stripped)
    if m is None:
        return None

    verb = m.group("verb").strip()
    rest = m.group("rest")

    scope_match = _SCOPE_SUFFIX_RE.search(rest)
    scope = scope_match.group("scope") if scope_match else None
    summary = _SCOPE_SUFFIX_RE.sub("", rest).strip()

    _, refs = _parse_refs(rest)

    return {
        "verb": verb,
        "summary": summary,
        "scope": scope,
        "refs": refs,
        "time": m.groupdict().get("time") if has_time else None,
    }


def _iter_dated_bullets(text: str) -> Iterator[tuple[str, dict]]:
    """Yield (date_str, parsed_bullet) for every parseable bullet under a
    ``## [YYYY-MM-DD]`` heading in *text*."""
    current_date: str | None = None
    for line in text.splitlines():
        date_match = _DATE_HEADING_RE.match(line)
        if date_match:
            current_date = date_match.group(1)
            continue
        if line.startswith("## "):
            current_date = None
            continue
        if current_date is None:
            continue
        parsed = _parse_bullet(line)
        if parsed is not None:
            yield current_date, parsed


def sync_from_files(conn: sqlite3.Connection, projects: list[dict]) -> dict:
    """Hydrate ``sb_ledger`` from bullets already present in each enrolled
    project's CHANGELOG.md. Never writes to any file. Idempotent via
    ``content_sha256`` (existing rows are silently skipped).

    Returns ``{"projects": {<project>: {"added": int, "skipped": int}}}``.
    """
    from .store.ledger import append_ledger

    results: dict[str, dict] = {}
    for project_row in projects:
        project = project_row["project"]
        changelog_path = Path(project_row["changelog_path"]).expanduser()
        added = 0
        skipped = 0

        if not changelog_path.is_file():
            results[project] = {"added": 0, "skipped": 0}
            continue

        text = changelog_path.read_text(encoding="utf-8")
        for date_str, bullet in _iter_dated_bullets(text):
            time_part = bullet["time"] or "00:00:00"
            ts = f"{date_str}T{time_part}Z"
            result = append_ledger(
                conn,
                project=project,
                summary=bullet["summary"],
                action_verb=bullet["verb"],
                scope=bullet["scope"],
                refs=bullet["refs"],
                source_harness="changelog-file",
                origin="hydrate",
                ts=ts,
            )
            if result["was_new"]:
                added += 1
            else:
                skipped += 1

        results[project] = {"added": added, "skipped": skipped}

    return {"projects": results}
