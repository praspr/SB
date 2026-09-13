"""FastMCP tool wrappers around the shared handler functions."""

from __future__ import annotations

from fastmcp import FastMCP

from . import handlers
from .db import get_conn
from .models import TodoCreate, TodoUpdate

mcp: FastMCP = FastMCP("sb-todos")


@mcp.tool()
def todo_list(
    status: str = "open",
    priority: int | None = None,
    domain: str | None = None,
    tag: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List todos with optional filters. status: open|completed|all."""
    conn = get_conn()
    todos = handlers.list_todos(
        conn, status=status, priority=priority, domain=domain, tag=tag, limit=limit
    )
    return [t.model_dump() for t in todos]


@mcp.tool()
def todo_get(todo_id: int) -> dict | None:
    """Fetch a single todo by id. Returns null if not found."""
    conn = get_conn()
    todo = handlers.get_todo(conn, todo_id)
    return todo.model_dump() if todo else None


@mcp.tool()
def todo_add(
    title: str,
    description: str = "",
    priority: int = 4,
    due_date: str | None = None,
    due_time: str | None = None,
    tags: list[str] | None = None,
    domain: str = "work",
    external_source: str | None = None,
    external_ref: str | None = None,
) -> dict:
    """Create a new todo. If external_source/external_ref match an existing
    todo, that todo is updated instead (idempotent upsert)."""
    conn = get_conn()
    data = TodoCreate(
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        due_time=due_time,
        tags=tags or [],
        domain=domain,
        external_source=external_source,
        external_ref=external_ref,
    )
    todo = handlers.add_todo(conn, data)
    return todo.model_dump()


@mcp.tool()
def todo_complete(todo_id: int) -> dict:
    """Mark a todo as completed."""
    conn = get_conn()
    todo = handlers.complete_todo(conn, todo_id)
    return todo.model_dump()


@mcp.tool()
def todo_uncomplete(todo_id: int) -> dict:
    """Mark a completed todo as not completed."""
    conn = get_conn()
    todo = handlers.uncomplete_todo(conn, todo_id)
    return todo.model_dump()


@mcp.tool()
def todo_update(
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    due_date: str | None = None,
    due_time: str | None = None,
    tags: list[str] | None = None,
    domain: str | None = None,
) -> dict:
    """Update the given fields of a todo. Only provided fields are changed."""
    conn = get_conn()
    data = TodoUpdate(
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        due_time=due_time,
        tags=tags,
        domain=domain,
    )
    todo = handlers.update_todo(conn, todo_id, data)
    return todo.model_dump()


@mcp.tool()
def todo_delete(todo_id: int) -> dict:
    """Delete a todo by id. Returns {"deleted": bool, "id": int}."""
    conn = get_conn()
    deleted = handlers.delete_todo(conn, todo_id)
    return {"deleted": deleted, "id": todo_id}


@mcp.tool()
def todo_search(query: str, limit: int = 20) -> list[dict]:
    """Search todos by title/description substring match."""
    conn = get_conn()
    todos = handlers.search_todos(conn, query, limit=limit)
    return [t.model_dump() for t in todos]
