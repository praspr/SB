#!/usr/bin/env python3
"""Sync JIRA issues from JSON (MCP search output) to ciq/docs/jira/."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

DEFAULT_OUTPUT = Path("/Users/praspr/Documents/code_home/ciq/docs/jira")

TERMINAL_STATUSES = frozenset({"Closed", "Done", "Cancelled"})

STATUS_EMOJI = {
    "Open": "📋 Open",
    "Closed": "✅ Closed",
    "Done": "✅ Closed",
    "Cancelled": "✅ Closed",
    "In Engineering Review": "🔶 In Engineering Review",
    "Concept Approved": "🔶 In Engineering Review",
    "Code Review": "🔶 In Engineering Review",
    "Dev Complete": "🔶 In Engineering Review",
    "In Testing": "🔶 In Engineering Review",
    "Test Complete": "🔶 In Engineering Review",
    "Blocked": "🔶 In Engineering Review",
}

STATUS_LINE_RE = re.compile(r"^\|\s\*\*Status\*\*\s\|\s(.+?)\s\|$", re.MULTILINE)
UPDATED_LINE_RE = re.compile(r"^\|\s\*\*Updated\*\*\s\|\s(.+?)\s\|$", re.MULTILINE)
TITLE_LINE_RE = re.compile(r"^#\s([A-Z]+-\d+)\s—\s(.+)$", re.MULTILINE)
RESOLUTION_LINE_RE = re.compile(
    r"^\|\s\*\*Resolution\*\*\s\|\s(.+?)\s\|$", re.MULTILINE
)


def status_emoji(name: str) -> str:
    return STATUS_EMOJI.get(name, f"🔶 {name}")


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def fmt_updated(raw: str) -> str:
    return datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S").strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def labels_str(labels: list[str] | None) -> str:
    return ", ".join(labels) if labels else "None"


def parent_str(parent: dict | None) -> str:
    if not parent:
        return "N/A"
    return f"{parent['key']} — {parent['fields']['summary']}"


def desc_str(desc: object) -> str:
    if not desc:
        return "_No description in JIRA._"
    if isinstance(desc, str):
        return desc.strip() or "_No description in JIRA._"
    return "_Description stored in ADF format — see JIRA for full content._"


def removed_summary_from_issue(issue: dict) -> str:
    f = issue["fields"]
    status = f["status"]["name"]
    resolution = (f.get("resolution") or {}).get("name")
    title = f["summary"]
    if len(title) > 80:
        title = title[:77] + "..."
    if resolution:
        return f"{status} ({resolution}). {title}"
    return f"{status}. {title}"


def removed_summary_from_file(path: Path) -> str:
    text = path.read_text()
    status_m = STATUS_LINE_RE.search(text)
    resolution_m = RESOLUTION_LINE_RE.search(text)
    title_m = TITLE_LINE_RE.search(text)
    status = status_m.group(1).strip() if status_m else "Closed"
    resolution = resolution_m.group(1).strip() if resolution_m else None
    title = title_m.group(2).strip() if title_m else path.stem
    if resolution and resolution not in ("Unresolved", "None"):
        return f"{status} ({resolution}). {title}"
    return f"{status}. {title}"


def updated_from_file(path: Path) -> str:
    text = path.read_text()
    updated_m = UPDATED_LINE_RE.search(text)
    if updated_m:
        raw = updated_m.group(1).strip()
        if "UTC" in raw:
            return raw.split("(")[0].strip() + (
                " UTC" if not raw.endswith("UTC") else ""
            )
        return f"{raw[:10]} 00:00:00 UTC"
    return f"{date.today().isoformat()} 00:00:00 UTC"


def ticket_markdown(issue: dict, sync_date: str) -> str:
    key = issue["key"]
    f = issue["fields"]
    summary = f["summary"]
    status = f["status"]["name"]
    itype = f["issuetype"]["name"]
    priority = (f.get("priority") or {}).get("name", "None")
    assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
    reporter = (f.get("reporter") or {}).get("displayName", "Unknown")
    labels = f.get("labels") or []
    parent = f.get("parent")
    description = desc_str(f.get("description"))
    updated = f.get("updated", "")[:10]
    created = f.get("created", "")[:10]
    resolution = (f.get("resolution") or {}).get("name")

    return f"""# {key} — {summary}

| Field | Value |
|-------|-------|
| **Key** | [{key}](https://cisco-cxe.atlassian.net/browse/{key}) |
| **Status** | {status} |
| **Priority** | {priority} |
| **Type** | {itype} |
| **Assignee** | {assignee} |
| **Reporter** | {reporter} |
| **Labels** | {labels_str(labels)} |
| **Parent** | {parent_str(parent)} |
| **Created** | {created} |
| **Updated** | {updated} |
| **Resolution** | {resolution or 'Unresolved'} |

---

## Context

Synced from JIRA on {sync_date}.

---

## Feature Description / Requirements

{description}

---

## Notes

- Last synced: {sync_date}
- Source: [JIRA](https://cisco-cxe.atlassian.net/browse/{key})
"""


def parse_ticket_file(path: Path) -> dict | None:
    text = path.read_text()
    key_m = re.match(r"^#\s([A-Z]+-\d+)\s—\s(.+)$", text, re.MULTILINE)
    status_m = STATUS_LINE_RE.search(text)
    if not key_m or not status_m:
        return None
    key = key_m.group(1)
    summary = key_m.group(2)
    status = status_m.group(1).strip()
    updated_m = UPDATED_LINE_RE.search(text)
    updated = updated_m.group(1).strip()[:10] if updated_m else "1970-01-01"
    type_m = re.search(r"^\|\s\*\*Type\*\*\s\|\s(.+?)\s\|$", text, re.MULTILINE)
    itype = type_m.group(1).strip() if type_m else "Unknown"
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status},
            "issuetype": {"name": itype},
            "updated": updated,
        },
    }


def write_readme(
    issues: list[dict],
    out: Path,
    sync_date: str,
    jql: str,
    *,
    assignee: str | None = None,
) -> None:
    rows = []
    for issue in issues:
        f = issue["fields"]
        key = issue["key"]
        status = f["status"]["name"]
        if is_terminal(status):
            continue
        summary = f["summary"]
        itype = f["issuetype"]["name"]
        updated = f.get("updated", "")[:10]
        rows.append((key, summary, status_emoji(status), itype, updated))

    rows.sort(key=lambda r: r[4], reverse=True)

    if assignee is None:
        assignee = "Unknown"
        if issues:
            assignee = (issues[0]["fields"].get("assignee") or {}).get(
                "displayName", "Unknown"
            )

    lines = [
        f"# JIRA Tickets — {assignee}",
        "",
        f"Local mirror under `{out}`.",
        "",
        f"> **Last synced:** {sync_date}  ",
        "> **Source:** [cisco-cxe.atlassian.net](https://cisco-cxe.atlassian.net)  ",
        "> **Policy:** Closed/Done/Cancelled tickets are removed from this mirror; "
        "summaries retained in [`tickethistory.md`](tickethistory.md).  ",
    ]
    if jql:
        lines.append(f"> **Query:** `{jql}`")
    lines.extend(
        [
            "",
            f"## Ticket index ({len(rows)} active tickets)",
            "",
            "| File | Ticket | Title | Status | Type | Updated |",
            "|------|--------|-------|--------|------|---------|",
        ]
    )

    for key, summary, emoji_status, itype, updated in rows:
        title = summary.replace("|", "\\|")
        if len(title) > 70:
            title = title[:67] + "..."
        lines.append(
            f"| [tickets/{key}.md](tickets/{key}.md) | "
            f"[{key}](https://cisco-cxe.atlassian.net/browse/{key}) | "
            f"{title} | {emoji_status} | {itype} | {updated} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "Maintained per `~/.claude/skills/jira-workflow/`.",
            "",
        ]
    )
    (out / "README.md").write_text("\n".join(lines))


def append_history_rows(
    out: Path,
    sync_date: str,
    rows: list[tuple[str, str, str, str]],
    marker: str | None = None,
) -> None:
    """Append history rows: (key, change_type, last_updated_on, description)."""
    if not rows:
        return

    history_path = out / "tickethistory.md"
    if history_path.exists():
        existing = history_path.read_text()
    else:
        existing = (
            "# JIRA Sync History — docs/jira\n\n"
            "| Date | Ticket | Change Type | Last Updated On | Description |\n"
            "|------|--------|-------------|-----------------|-------------|\n"
        )

    if marker and marker in existing:
        print(f"Skip history: {marker} already recorded", file=sys.stderr)
        return

    formatted = [
        f"| {sync_date} | {key} | **{ctype}** | {updated} | {desc} |"
        for key, ctype, updated, desc in rows
    ]
    block = "\n"
    if marker:
        block += marker + "\n"
    block += "\n".join(formatted) + "\n"
    history_path.write_text(existing.rstrip() + "\n" + block)


def purge_ticket(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def scan_and_purge_stale_closed(
    tickets_dir: Path,
    sync_date: str,
    out: Path,
    *,
    skip_keys: set[str],
) -> list[str]:
    """Remove on-disk ticket files with terminal status not handled this run."""
    removed_keys: list[str] = []
    rows: list[tuple[str, str, str, str]] = []

    for path in sorted(tickets_dir.glob("*.md")):
        key = path.stem
        if key in skip_keys:
            continue
        status_m = STATUS_LINE_RE.search(path.read_text())
        if not status_m:
            continue
        status = status_m.group(1).strip()
        if not is_terminal(status):
            continue
        summary = removed_summary_from_file(path)
        updated = updated_from_file(path)
        purge_ticket(path)
        removed_keys.append(key)
        rows.append((key, "Removed", updated, summary))

    if rows:
        marker = f"<!-- Stale closed purge {sync_date} -->"
        append_history_rows(out, sync_date, rows, marker=marker)

    return removed_keys


def sync_issues(
    issues: list[dict],
    output_dir: Path,
    jql: str,
    *,
    scan_stale: bool = True,
) -> tuple[int, int]:
    sync_date = date.today().isoformat()
    tickets_dir = output_dir / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)

    active_issues: list[dict] = []
    history_rows: list[tuple[str, str, str, str]] = []
    handled_keys: set[str] = set()
    purged_count = 0

    for issue in issues:
        key = issue["key"]
        handled_keys.add(key)
        f = issue["fields"]
        status = f["status"]["name"]
        updated = fmt_updated(f["updated"])
        ticket_path = tickets_dir / f"{key}.md"

        if is_terminal(status):
            had_file = ticket_path.exists()
            if had_file:
                purge_ticket(ticket_path)
                history_rows.append(
                    (key, "Removed", updated, removed_summary_from_issue(issue))
                )
                purged_count += 1
                print(f"Purge {key} ({status})", file=sys.stderr)
            else:
                print(f"Skip {key} ({status}) — already purged", file=sys.stderr)
        else:
            ticket_path.write_text(ticket_markdown(issue, sync_date))
            active_issues.append(issue)
            history_rows.append(
                (key, "Synced", updated, f"Pulled from JIRA. Status: {status}.")
            )

    marker = f"<!-- Bulk sync {sync_date} -->"
    append_history_rows(output_dir, sync_date, history_rows, marker=marker)

    removed_stale: list[str] = []
    if scan_stale:
        removed_stale = scan_and_purge_stale_closed(
            tickets_dir, sync_date, output_dir, skip_keys=handled_keys
        )
        purged_count += len(removed_stale)

    # README from all active on-disk tickets + metadata from sync batch
    issue_by_key = {i["key"]: i for i in active_issues}
    disk_active: list[dict] = []
    for path in sorted(tickets_dir.glob("*.md")):
        key = path.stem
        if key in issue_by_key:
            disk_active.append(issue_by_key[key])
        else:
            parsed = parse_ticket_file(path)
            if parsed and not is_terminal(parsed["fields"]["status"]["name"]):
                disk_active.append(parsed)

    assignee = None
    if issues:
        assignee = (issues[0]["fields"].get("assignee") or {}).get("displayName")

    write_readme(disk_active, output_dir, sync_date, jql, assignee=assignee)

    return len(active_issues), purged_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync JIRA JSON to docs/jira/")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help='JSON file with {"issues": [...]} from MCP (stdin if omitted)',
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--jql",
        default="assignee = currentUser() ORDER BY updated DESC",
        help="JQL query (recorded in README)",
    )
    parser.add_argument(
        "--no-scan-stale",
        action="store_true",
        help="Skip scanning on-disk tickets for stale closed status",
    )
    args = parser.parse_args()

    if args.input:
        data = json.loads(args.input.read_text())
    else:
        data = json.load(sys.stdin)

    issues = data.get("issues", [])
    if not issues:
        print("No issues in input", file=sys.stderr)
        return 1

    active, purged = sync_issues(
        issues,
        args.output_dir,
        args.jql,
        scan_stale=not args.no_scan_stale,
    )
    print(
        f"Synced {active} active tickets, purged {purged} closed; "
        f"output {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
