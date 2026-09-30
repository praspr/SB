"""Parse local JIRA ticket markdown mirrors into JiraTicket / JiraTicketDetail models.

Ticket file shape (see ciq/docs/jira/tickets/*.md):

    # CXP-46855 — <Title>

    | Field | Value |
    |-------|-------|
    | **Key** | [CXP-46855](https://cisco-cxe.atlassian.net/browse/CXP-46855) |
    | **Status** | Code Review |
    | **Priority** | Medium |
    | **Type** | Story |
    | **Assignee** | PRASAD P R |
    | **Reporter** | PRASAD P R |
    | **Labels** | label-a, label-b |
    | **Parent** | CXP-46583 — Some Epic |
    | **Created** | 2026-08-07 |
    | **Updated** | 2026-08-19 |
    | **Resolution** | Unresolved |

    ---

    ## Context

    ...

    ---

    ## Feature Description / Requirements

    ...

Robust to formatting quirks: extra whitespace, missing optional fields,
non-table rows. If parsing fails for a single file we log a warning and
skip it rather than raising, so the list endpoint never crashes wholesale.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import settings
from .models import JiraTicket, JiraTicketDetail, Person, Section

logger = logging.getLogger("sb_jira.file_store")

# Known name -> email mapping for people encountered in the local mirror.
# Extend as new assignees/reporters show up.
KNOWN_EMAILS: dict[str, str] = {
    "PRASAD P R": "praspr@cisco.com",
}

H1_RE = re.compile(r"^#\s+(?P<key>[A-Z][A-Z0-9]*-\d+)\s+—\s*(?P<title>.*)$")
TABLE_ROW_RE = re.compile(r"^\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|\s*(.*?)\s*\|\s*$")
KEY_LINK_RE = re.compile(r"\[([A-Z][A-Z0-9]*-\d+)\]\((https?://\S+)\)")


def _guess_email(name: str) -> str:
    name = name.strip()
    if not name:
        return ""
    if name in KNOWN_EMAILS:
        return KNOWN_EMAILS[name]
    # Best-effort fallback: "First Last" -> first.last@cisco.com
    slug = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").split()
    if not slug:
        return ""
    return ".".join(slug) + "@cisco.com"


def _parse_person(raw: str) -> Person | None:
    raw = raw.strip()
    if not raw or raw.lower() in {"unassigned", "none", "-", "n/a"}:
        return None
    # Support "Name (email@domain)" as well as bare "Name"
    m = re.match(r"^(?P<name>.+?)\s*\((?P<email>[^)]+@[^)]+)\)\s*$", raw)
    if m:
        return Person(name=m.group("name").strip(), email=m.group("email").strip())
    return Person(name=raw, email=_guess_email(raw))


def _split_labels(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw or raw.lower() in {"none", "-", "n/a"}:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _first_n_chars(text: str, n: int = 200) -> str:
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "…"


class ParsedTicketFile:
    """Intermediate representation before building pydantic models."""

    def __init__(
        self,
        key: str,
        title: str,
        fields: dict[str, str],
        sections: list[Section],
    ) -> None:
        self.key = key
        self.title = title
        self.fields = fields
        self.sections = sections


def parse_str(text: str, file_path: str = "") -> JiraTicketDetail:
    """Parse full markdown text of a ticket file into a JiraTicketDetail."""
    lines = text.splitlines()

    # 1. H1 heading -> key + title
    key = ""
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        m = H1_RE.match(line.strip())
        if m:
            key = m.group("key")
            title = m.group("title").strip()
            body_start = i + 1
            break
    if not key:
        raise ValueError("no '# KEY — Title' heading found")

    # 2. Metadata table rows (until first '---' line)
    fields: dict[str, str] = {}
    sep_idx: int | None = None
    for i in range(body_start, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if stripped == "---":
            sep_idx = i
            break
        if stripped.startswith("|"):
            m = TABLE_ROW_RE.match(stripped)
            if m:
                field_name = m.group(1).strip()
                value = m.group(2).strip()
                if field_name.lower() in {"field", "---", ""}:
                    continue
                fields[field_name] = value

    if sep_idx is None:
        sep_idx = len(lines)

    # 3. Everything after the first '---': split into '## ' sections.
    remainder = "\n".join(lines[sep_idx + 1 :])
    sections = _parse_sections(remainder)

    # --- Derive model fields ---
    url = fields.get("URL", "").strip()
    if not url:
        key_val = fields.get("Key", "")
        lm = KEY_LINK_RE.search(key_val)
        if lm:
            url = lm.group(2)
        else:
            url = f"{settings.atlassian_site}/browse/{key}"

    status = fields.get("Status", "").strip() or "Open"
    priority = fields.get("Priority", "").strip() or "Medium"
    issue_type = fields.get("Type", "").strip() or "Task"

    assignee = _parse_person(fields.get("Assignee", "")) or Person(
        name="Unassigned", email=""
    )
    reporter = _parse_person(fields.get("Reporter", ""))

    created = fields.get("Created", "").strip()
    updated = fields.get("Updated", "").strip()

    labels = _split_labels(fields.get("Labels", ""))
    fix_versions = _split_labels(fields.get("Fix Versions", ""))

    project = key.split("-")[0]

    description_section = None
    for s in sections:
        if s.name.lower() in {
            "context",
            "feature description / requirements",
            "feature description",
        }:
            description_section = s
            break
    if description_section is None and sections:
        description_section = sections[0]

    description_md = description_section.body if description_section else ""
    description = _first_n_chars(description_md, 200)

    return JiraTicketDetail(
        key=key,
        project=project,
        title=title,
        status=status,
        priority=priority,
        issue_type=issue_type,
        assignee=assignee,
        reporter=reporter,
        created=created,
        updated=updated,
        labels=labels,
        fix_versions=fix_versions,
        description=description,
        url=url,
        file_path=file_path,
        description_md=description_md,
        sections=sections,
    )


def _parse_sections(text: str) -> list[Section]:
    """Split remainder text into ## headed sections. Strips bare '---' separator lines."""
    sections: list[Section] = []
    lines = text.splitlines()
    current_name: str | None = None
    current_body: list[str] = []

    def flush() -> None:
        if current_name is not None:
            body = "\n".join(current_body).strip()
            # Strip lone '---' separator lines that appear between sections.
            body = re.sub(r"\n?^---$\n?", "\n", body, flags=re.MULTILINE).strip()
            sections.append(Section(name=current_name, body=body))

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            flush()
            current_name = stripped[3:].strip()
            current_body = []
        else:
            current_body.append(line)
    flush()
    return sections


def load(file_path: Path) -> JiraTicketDetail:
    text = file_path.read_text(encoding="utf-8")
    rel = _relative_path(file_path)
    return parse_str(text, file_path=rel)


def _relative_path(file_path: Path) -> str:
    try:
        rel = file_path.relative_to(settings.code_home)
        return str(rel)
    except ValueError:
        return str(file_path)


def load_all(tickets_dir: Path | None = None) -> list[JiraTicketDetail]:
    """Load and parse every *.md ticket file in the tickets directory.

    Individual parse failures are logged and skipped; they never crash the
    whole listing.
    """
    directory = tickets_dir or settings.tickets_dir
    tickets: list[JiraTicketDetail] = []
    if not directory.exists():
        logger.warning("tickets dir does not exist: %s", directory)
        return tickets

    for path in sorted(directory.glob("*.md")):
        try:
            tickets.append(load(path))
        except (
            Exception
        ) as exc:  # noqa: BLE001 - intentional broad catch, per-file isolation
            logger.warning("failed to parse ticket file %s: %s", path, exc)
            continue
    return tickets


def load_all_as_dict(tickets_dir: Path | None = None) -> dict[str, JiraTicketDetail]:
    return {t.key: t for t in load_all(tickets_dir)}


def to_ticket(detail: JiraTicketDetail) -> JiraTicket:
    """Downcast a JiraTicketDetail to the base JiraTicket shape."""
    return JiraTicket(**detail.model_dump(exclude={"description_md", "sections"}))


def load_by_key(key: str, tickets_dir: Path | None = None) -> JiraTicketDetail | None:
    """Load a single ticket by key, or None if it doesn't exist / fails to parse."""
    directory = tickets_dir or settings.tickets_dir
    path = directory / f"{key}.md"
    if not path.exists():
        return None
    try:
        return load(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to parse ticket file %s: %s", path, exc)
        return None


def apply_filters(
    tickets: list[JiraTicket],
    status: str | None = None,
    priority: str | None = None,
    project: str | None = None,
    q: str | None = None,
) -> list[JiraTicket]:
    """Shared filter logic used by both the REST `/api/jira/tickets` endpoint
    and the `list_jira_tickets` MCP tool, so results stay identical.
    """
    result = tickets
    if status:
        result = [t for t in result if t.status == status]
    if priority:
        result = [t for t in result if t.priority == priority]
    if project:
        result = [t for t in result if t.project == project]
    if q:
        needle = q.lower()
        result = [t for t in result if needle in f"{t.key} {t.title}".lower()]
    # Match docs/jira/README.md: newest update first.
    result.sort(key=lambda ticket: ticket.updated or "", reverse=True)
    return result
