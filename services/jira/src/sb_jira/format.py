"""Write JiraTicketDetail back to markdown, matching the exact layout used by
`ciq/docs/jira/tickets/*.md` (per the jira-workflow skill / real ticket files).
"""

from __future__ import annotations

from .config import settings
from .models import JiraTicketDetail

METADATA_ROWS = [
    "Key",
    "Status",
    "Priority",
    "Type",
    "Assignee",
    "Reporter",
    "Labels",
    "Fix Versions",
    "Created",
    "Updated",
]

DEFAULT_SECTION_ORDER = [
    "Context",
    "Feature Description / Requirements",
    "Acceptance Criteria",
    "Notes",
]


def _person_str(person) -> str:  # type: ignore[no-untyped-def]
    if person is None:
        return "Unassigned"
    if person.email:
        return f"{person.name} ({person.email})"
    return person.name


def to_markdown(ticket: JiraTicketDetail) -> str:
    lines: list[str] = []
    lines.append(f"# {ticket.key} — {ticket.title}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| **Key** | [{ticket.key}]({ticket.url}) |")
    lines.append(f"| **Status** | {ticket.status} |")
    lines.append(f"| **Priority** | {ticket.priority} |")
    lines.append(f"| **Type** | {ticket.issue_type} |")
    lines.append(f"| **Assignee** | {_person_str(ticket.assignee)} |")
    if ticket.reporter is not None:
        lines.append(f"| **Reporter** | {_person_str(ticket.reporter)} |")
    lines.append(f"| **Labels** | {', '.join(ticket.labels) if ticket.labels else 'None'} |")
    if ticket.fix_versions:
        lines.append(f"| **Fix Versions** | {', '.join(ticket.fix_versions)} |")
    lines.append(f"| **Created** | {ticket.created} |")
    lines.append(f"| **Updated** | {ticket.updated} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    sections = ticket.sections or []
    section_by_name = {s.name: s for s in sections}

    # Emit sections in the canonical order first, then any extras verbatim.
    emitted: set[str] = set()
    ordered_names = [n for n in DEFAULT_SECTION_ORDER if n in section_by_name]
    ordered_names += [s.name for s in sections if s.name not in DEFAULT_SECTION_ORDER]

    for idx, name in enumerate(ordered_names):
        if name in emitted:
            continue
        emitted.add(name)
        section = section_by_name[name]
        lines.append(f"## {name}")
        lines.append("")
        if section.body:
            lines.append(section.body)
            lines.append("")
        if idx < len(ordered_names) - 1:
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def file_path_for(key: str) -> str:
    return f"{settings.relative_tickets_prefix}/{key}.md"
