"""FastAPI REST router mirroring the MCP tool surface via shared handlers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from . import handlers
from .db import get_conn
from .models import Todo, TodoCreate, TodoUpdate

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get("", response_model=list[Todo])
def api_list_todos(
    status: str = Query(default="open"),
    priority: int | None = Query(default=None),
    domain: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=100),
) -> list[Todo]:
    conn = get_conn()
    try:
        return handlers.list_todos(
            conn, status=status, priority=priority, domain=domain, tag=tag, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/search", response_model=list[Todo])
def api_search_todos(q: str = Query(...), limit: int = Query(default=20)) -> list[Todo]:
    conn = get_conn()
    return handlers.search_todos(conn, q, limit=limit)


@router.get("/{todo_id}", response_model=Todo)
def api_get_todo(todo_id: int) -> Todo:
    conn = get_conn()
    todo = handlers.get_todo(conn, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} not found")
    return todo


@router.post("", response_model=Todo, status_code=201)
def api_add_todo(data: TodoCreate) -> Todo:
    conn = get_conn()
    return handlers.add_todo(conn, data)


@router.patch("/{todo_id}", response_model=Todo)
def api_update_todo(todo_id: int, data: TodoUpdate) -> Todo:
    conn = get_conn()
    try:
        return handlers.update_todo(conn, todo_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{todo_id}/complete", response_model=Todo)
def api_complete_todo(todo_id: int) -> Todo:
    conn = get_conn()
    try:
        return handlers.complete_todo(conn, todo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{todo_id}/uncomplete", response_model=Todo)
def api_uncomplete_todo(todo_id: int) -> Todo:
    conn = get_conn()
    try:
        return handlers.uncomplete_todo(conn, todo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{todo_id}")
def api_delete_todo(todo_id: int) -> dict:
    conn = get_conn()
    deleted = handlers.delete_todo(conn, todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} not found")
    return {"deleted": True, "id": todo_id}
