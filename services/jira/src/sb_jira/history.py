"""Update README.md ticket index and append rows to tickethistory.md.

Both files are rewritten/appended atomically via a temp file + os.replace.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path

from .config import settings
from .models import JiraTicketDetail

STATUS_EMOJI: dict[str, str] = {
    "open": "📋 Open",
    "closed": "✅ Closed",
    "done": "✅ Closed",
    "cancelled": "✅ Closed",
    "in engineering review": "🔶 In Engineering Review",
    "concept approved": "🔶 In Engineering Review",
    "code review": "🔶 In Engineering Review",
    "dev complete": "🔶 In Engineering Review",
    "in testing": "🔶 In Engineering Review",
    "test complete": "🔶 In Engineering Review",
    "blocked": "🔶 In Engineering Review",
}

TERMINAL_STATUSES = {"closed", "done", "cancelled"}


def status_label(status: str) -> str:
    return STATUS_EMOJI.get(status.strip().lower(), f"📋 {status}")


def is_terminal(status: str) -> bool:
    return status.strip().lower() in TERMINAL_STATUSES


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def regenerate_readme(tickets: list[JiraTicketDetail], readme_path: Path | None = None) -> None:
    """Regenerate the ticket index table in README.md, sorted by updated desc.

    Preserves any content before the '## Ticket index' heading (or the whole
    file, if the heading isn't found, appending the table at the end) so we
    don't clobber narrative sections maintained by hand.
    """
    path = readme_path or settings.readme_path
    if not path.exists():
        header = "# JIRA Tickets\n\n"
        existing = header
    else:
        existing = path.read_text(encoding="utf-8")

    sorted_tickets = sorted(tickets, key=lambda t: t.updated, reverse=True)

    table_lines = [
        f"## Ticket index ({len(sorted_tickets)} active tickets)",
        "",
        "| File | Ticket | Title | Status | Type | Updated |",
        "|------|--------|-------|--------|------|---------|",
    ]
    for t in sorted_tickets:
        file_link = f"tickets/{t.key}.md"
        table_lines.append(
            f"| [{file_link}]({file_link}) | [{t.key}]({t.url}) | {t.title} | "
            f"{status_label(t.status)} | {t.issue_type} | {t.updated[:10]} |"
        )
    table_md = "\n".join(table_lines) + "\n"

    index_heading_re = re.compile(r"^## Ticket index.*$", re.MULTILINE)
    m = index_heading_re.search(existing)
    if m:
        # Replace from the heading up to (but not including) the next '---'
        # or '## ' heading that starts a new section, or end of file.
        start = m.start()
        rest = existing[m.end() :]
        next_section = re.search(r"\n---\n|\n## (?!Ticket index)", rest)
        end = m.end() + (next_section.start() if next_section else len(rest))
        new_content = existing[:start] + table_md + existing[end:]
    else:
        sep = "\n---\n\n" if not existing.endswith("\n\n") else "---\n\n"
        new_content = existing.rstrip() + "\n\n" + table_md

    _atomic_write(path, new_content)


def append_history_row(
    updated_count: int,
    added_count: int,
    last_updated_on: str,
    history_path: Path | None = None,
    today: date | None = None,
) -> None:
    path = history_path or settings.tickethistory_path
    today_str = (today or datetime.now().date()).isoformat()
    row = (
        f"| {today_str} | SYNC | Bulk sync | {last_updated_on} | "
        f"Synced from Atlassian: {updated_count} updated, {added_count} added |\n"
    )

    if not path.exists():
        header = (
            "# JIRA Sync History — docs/jira\n\n"
            "| Date | Ticket | Change Type | Last Updated On | Description |\n"
            "|------|--------|-------------|-----------------|-------------|\n\n"
        )
        _atomic_write(path, header + row)
        return

    existing = path.read_text(encoding="utf-8")
    new_content = existing.rstrip("\n") + "\n" + row
    _atomic_write(path, new_content)
