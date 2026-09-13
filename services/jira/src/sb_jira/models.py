"""Pydantic response models — must match the sb web app's TypeScript `JiraTicket` type."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Person(BaseModel):
    name: str
    email: str = ""


class JiraTicket(BaseModel):
    key: str  # 'CXP-45827'
    project: str  # 'CXP'
    title: str
    status: str  # 'Open' | 'In Engineering Review' | 'Closed' | ...
    priority: str  # 'Highest' | 'High' | 'Medium' | 'Low' | 'Lowest'
    issue_type: str  # 'Bug' | 'Task' | 'Story' | 'Epic' | 'Sub-task'
    assignee: Person
    reporter: Person | None = None
    created: str  # ISO datetime
    updated: str  # ISO datetime
    labels: list[str] = Field(default_factory=list)
    fix_versions: list[str] = Field(default_factory=list)
    description: str = ""  # short summary text (~200 chars)
    url: str  # 'https://cisco-cxe.atlassian.net/browse/{key}'
    file_path: str = ""  # 'ciq/docs/jira/tickets/{KEY}.md'


class Section(BaseModel):
    name: str
    body: str


class JiraTicketDetail(JiraTicket):
    description_md: str = ""  # full description markdown
    sections: list[Section] = Field(default_factory=list)


class RefreshResult(BaseModel):
    updated_count: int = 0
    added_count: int = 0
    unchanged_count: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    history_row_appended: bool = False


class StatusResponse(BaseModel):
    last_sync_at: str | None = None
    atlassian_reachable: bool = False
    atlassian_error: str | None = None
    tickets_count: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    tickets_on_disk: int = 0
