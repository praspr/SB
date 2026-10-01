"""Tests for handlers.py — full CRUD round-trip against an in-memory DB."""

import pytest

from sb_todos import handlers
from sb_todos.models import TodoCreate, TodoUpdate


def test_add_and_get_todo(conn):
    created = handlers.add_todo(conn, TodoCreate(title="Buy milk", priority=2))
    assert created.id is not None
    assert created.title == "Buy milk"
    assert created.priority == 2
    assert created.is_completed is False

    fetched = handlers.get_todo(conn, created.id)
    assert fetched is not None
    assert fetched.title == "Buy milk"


def test_get_todo_not_found(conn):
    assert handlers.get_todo(conn, 9999) is None


def test_list_todos_status_filter(conn):
    a = handlers.add_todo(conn, TodoCreate(title="Open one"))
    b = handlers.add_todo(conn, TodoCreate(title="Will complete"))
    handlers.complete_todo(conn, b.id)

    open_todos = handlers.list_todos(conn, status="open")
    assert [t.id for t in open_todos] == [a.id]

    completed_todos = handlers.list_todos(conn, status="completed")
    assert [t.id for t in completed_todos] == [b.id]

    all_todos = handlers.list_todos(conn, status="all")
    assert {t.id for t in all_todos} == {a.id, b.id}


def test_list_todos_invalid_status(conn):
    with pytest.raises(ValueError):
        handlers.list_todos(conn, status="bogus")


def test_list_todos_priority_domain_tag_filters(conn):
    handlers.add_todo(
        conn, TodoCreate(title="P1 work", priority=1, domain="work", tags=["urgent"])
    )
    handlers.add_todo(
        conn, TodoCreate(title="P3 personal", priority=3, domain="personal", tags=["chore"])
    )

    p1 = handlers.list_todos(conn, priority=1)
    assert len(p1) == 1 and p1[0].title == "P1 work"

    personal = handlers.list_todos(conn, domain="personal")
    assert len(personal) == 1 and personal[0].title == "P3 personal"

    tagged = handlers.list_todos(conn, tag="urgent")
    assert len(tagged) == 1 and tagged[0].title == "P1 work"


def test_complete_and_uncomplete(conn):
    todo = handlers.add_todo(conn, TodoCreate(title="Task"))
    completed = handlers.complete_todo(conn, todo.id)
    assert completed.is_completed is True
    assert completed.completed_at is not None

    uncompleted = handlers.uncomplete_todo(conn, todo.id)
    assert uncompleted.is_completed is False
    assert uncompleted.completed_at is None


def test_complete_not_found(conn):
    with pytest.raises(ValueError):
        handlers.complete_todo(conn, 12345)


def test_update_todo_partial(conn):
    todo = handlers.add_todo(conn, TodoCreate(title="Original", priority=4))
    updated = handlers.update_todo(conn, todo.id, TodoUpdate(title="Renamed"))
    assert updated.title == "Renamed"
    assert updated.priority == 4  # unchanged


def test_update_todo_tags(conn):
    todo = handlers.add_todo(conn, TodoCreate(title="Task"))
    updated = handlers.update_todo(conn, todo.id, TodoUpdate(tags=["a", "b"]))
    assert updated.tags == ["a", "b"]


def test_update_todo_not_found(conn):
    with pytest.raises(ValueError):
        handlers.update_todo(conn, 12345, TodoUpdate(title="x"))


def test_due_time_and_reminder_round_trip(conn):
    created = handlers.add_todo(
        conn,
        TodoCreate(
            title="Prep release note",
            due_date="2026-10-02",
            due_time="15:30",
            remind_before_minutes=20,
        ),
    )

    assert created.due_date == "2026-10-02"
    assert created.due_time == "15:30"
    assert created.remind_before_minutes == 20

    updated = handlers.update_todo(
        conn,
        created.id,
        TodoUpdate(due_time=None, remind_before_minutes=None),
    )

    assert updated.due_date == "2026-10-02"
    assert updated.due_time is None
    assert updated.remind_before_minutes is None


def test_delete_todo(conn):
    todo = handlers.add_todo(conn, TodoCreate(title="Temp"))
    assert handlers.delete_todo(conn, todo.id) is True
    assert handlers.get_todo(conn, todo.id) is None
    assert handlers.delete_todo(conn, todo.id) is False


def test_search_todos(conn):
    handlers.add_todo(conn, TodoCreate(title="Fix the bug", description="urgent"))
    handlers.add_todo(conn, TodoCreate(title="Write docs", description="fix typos"))
    handlers.add_todo(conn, TodoCreate(title="Unrelated"))

    results = handlers.search_todos(conn, "fix")
    titles = {t.title for t in results}
    assert titles == {"Fix the bug", "Write docs"}


def test_add_todo_external_ref_upsert(conn):
    first = handlers.add_todo(
        conn,
        TodoCreate(
            title="CXP-1: initial",
            external_source="jira",
            external_ref="CXP-1",
        ),
    )
    second = handlers.add_todo(
        conn,
        TodoCreate(
            title="CXP-1: updated title",
            priority=1,
            external_source="jira",
            external_ref="CXP-1",
        ),
    )

    assert second.id == first.id
    assert second.title == "CXP-1: updated title"
    assert second.priority == 1

    all_todos = handlers.list_todos(conn, status="all")
    assert len(all_todos) == 1
