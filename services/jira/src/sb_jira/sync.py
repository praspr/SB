"""Atlassian -> local files sync. SAFE, ATOMIC, one-directional.

Never writes to Atlassian. Never deletes local ticket files for tickets that
are simply missing from the remote fetch (orphans are left alone and logged).
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from . import atlassian_client, file_store, format, history
from .config import settings
from .models import JiraTicketDetail, RefreshResult

logger = logging.getLogger("sb_jira.sync")


def _tickets_differ(a: JiraTicketDetail, b: JiraTicketDetail) -> bool:
    compare_fields = (
        "title",
        "status",
        "priority",
        "issue_type",
        "labels",
        "fix_versions",
        "updated",
        "description_md",
    )
    for field in compare_fields:
        if getattr(a, field) != getattr(b, field):
            return True
    if a.assignee != b.assignee:
        return True
    if a.reporter != b.reporter:
        return True
    return False


def _write_ticket_file(ticket: JiraTicketDetail, tickets_dir: Path) -> Path:
    path = tickets_dir / f"{ticket.key}.md"
    md = format.to_markdown(ticket)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(md, encoding="utf-8")
    os.replace(tmp, path)
    return path


def run_sync(tickets_dir: Path | None = None) -> RefreshResult:
    start = time.perf_counter()
    directory = tickets_dir or settings.tickets_dir
    errors: list[str] = []

    existing = file_store.load_all_as_dict(directory)

    try:
        remote_list = atlassian_client.fetch_all_assigned()
    except atlassian_client.AtlassianAuthError as exc:
        return RefreshResult(
            errors=[f"No Atlassian token — run `sb secret set jira.token` ({exc})"],
            duration_ms=(time.perf_counter() - start) * 1000,
        )
    except atlassian_client.AtlassianClientError as exc:
        return RefreshResult(
            errors=[f"Atlassian fetch failed: {exc}"],
            duration_ms=(time.perf_counter() - start) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return RefreshResult(
            errors=[f"Unexpected error contacting Atlassian: {exc}"],
            duration_ms=(time.perf_counter() - start) * 1000,
        )

    remote = {t.key: t for t in remote_list}

    updated_count = 0
    added_count = 0
    unchanged_count = 0

    for key, remote_ticket in remote.items():
        try:
            local_ticket = existing.get(key)
            remote_ticket.file_path = format.file_path_for(key)
            if local_ticket is None:
                _write_ticket_file(remote_ticket, directory)
                added_count += 1
            elif _tickets_differ(local_ticket, remote_ticket):
                _write_ticket_file(remote_ticket, directory)
                updated_count += 1
            else:
                unchanged_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to sync ticket %s: %s", key, exc)
            errors.append(f"{key}: {exc}")

    for key in existing:
        if key not in remote:
            logger.info("orphan local ticket (kept, not in remote fetch): %s", key)

    # Reload from disk to get the authoritative merged state for the README.
    all_tickets = file_store.load_all(directory)

    history_row_appended = False
    try:
        history.regenerate_readme(all_tickets)
        last_updated_on = atlassian_client.last_updated_utc(remote_list)
        history.append_history_row(updated_count, added_count, last_updated_on)
        history_row_appended = True
    except Exception as exc:  # noqa: BLE001
        logger.error("failed to update README/history: %s", exc)
        errors.append(f"README/history update failed: {exc}")

    duration_ms = (time.perf_counter() - start) * 1000
    return RefreshResult(
        updated_count=updated_count,
        added_count=added_count,
        unchanged_count=unchanged_count,
        errors=errors,
        duration_ms=duration_ms,
        history_row_appended=history_row_appended,
    )
