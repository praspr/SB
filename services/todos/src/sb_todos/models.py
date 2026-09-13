"""Pydantic models for sb-todos."""

from enum import IntEnum

from pydantic import BaseModel, Field


class Priority(IntEnum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


class Todo(BaseModel):
    id: int
    title: str
    description: str = ""
    priority: int = 4
    due_date: str | None = None
    due_time: str | None = None
    is_completed: bool = False
    completed_at: str | None = None
    tags: list[str] = []
    external_source: str | None = None
    external_ref: str | None = None
    domain: str = "work"
    created_at: str
    updated_at: str


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = ""
    priority: int = Field(default=4, ge=1, le=4)
    due_date: str | None = None
    due_time: str | None = None
    tags: list[str] = []
    external_source: str | None = None
    external_ref: str | None = None
    domain: str = "work"


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    due_date: str | None = None
    due_time: str | None = None
    tags: list[str] | None = None
    domain: str | None = None


class TodoFilter(BaseModel):
    status: str = "open"  # open | completed | all
    priority: int | None = None
    domain: str | None = None
    tag: str | None = None
    limit: int = 100


class SearchResult(BaseModel):
    query: str
    results: list[Todo]
