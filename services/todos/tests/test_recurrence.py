"""Tests for phase 2a: goal_id/jira_ref/recurrence_rule/parent_todo_id columns,
and the expand_recurring_todo engine."""

from __future__ import annotations

import pytest

from sb_todos import handlers
from sb_todos.models import TodoCreate, TodoUpdate


def test_add_todo_accepts_new_fields(conn):
    created = handlers.add_todo(
        conn,
        TodoCreate(
            title="Linked todo",
            goal_id=7,
            jira_ref="CXP-100",
            recurrence_rule="FREQ=DAILY",
        ),
    )
    assert created.goal_id == 7
    assert created.jira_ref == "CXP-100"
    assert created.recurrence_rule == "FREQ=DAILY"
    assert created.parent_todo_id is None


def test_update_todo_sets_new_fields(conn):
    created = handlers.add_todo(conn, TodoCreate(title="Plain todo"))
    updated = handlers.update_todo(
        conn, created.id, TodoUpdate(goal_id=3, jira_ref="CXP-200")
    )
    assert updated.goal_id == 3
    assert updated.jira_ref == "CXP-200"


def test_idempotent_upsert_preserves_new_fields(conn):
    first = handlers.add_todo(
        conn,
        TodoCreate(
            title="Imported ticket",
            external_source="jira",
            external_ref="CXP-300",
            jira_ref="CXP-300",
        ),
    )
    second = handlers.add_todo(
        conn,
        TodoCreate(
            title="Imported ticket (refreshed)",
            external_source="jira",
            external_ref="CXP-300",
            jira_ref="CXP-300",
            goal_id=5,
        ),
    )
    assert second.id == first.id
    assert second.title == "Imported ticket (refreshed)"
    assert second.goal_id == 5


# ---------------------------------------------------------------------------
# expand_recurring_todo
# ---------------------------------------------------------------------------


def test_expand_recurring_todo_daily(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(title="Daily standup prep", due_date="2026-09-30", recurrence_rule="FREQ=DAILY"),
    )
    next_instance = handlers.expand_recurring_todo(conn, template.id)
    assert next_instance is not None
    assert next_instance.due_date == "2026-10-01"
    assert next_instance.parent_todo_id == template.id
    assert next_instance.title == "Daily standup prep"
    assert next_instance.recurrence_rule == "FREQ=DAILY"


def test_expand_recurring_todo_weekly_byday(conn):
    # 2026-09-30 is a Wednesday.
    template = handlers.add_todo(
        conn,
        TodoCreate(
            title="Weekly review",
            due_date="2026-09-30",
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE",
        ),
    )
    next_instance = handlers.expand_recurring_todo(conn, template.id)
    assert next_instance.due_date == "2026-10-05"  # next Monday


def test_expand_recurring_todo_monthly_bymonthday(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(
            title="Monthly report",
            due_date="2026-09-15",
            recurrence_rule="FREQ=MONTHLY;BYMONTHDAY=1",
        ),
    )
    next_instance = handlers.expand_recurring_todo(conn, template.id)
    assert next_instance.due_date == "2026-10-01"


def test_expand_recurring_todo_monthly_clamps_short_month(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(
            title="End of month",
            due_date="2026-01-31",
            recurrence_rule="FREQ=MONTHLY;BYMONTHDAY=31",
        ),
    )
    next_instance = handlers.expand_recurring_todo(conn, template.id)
    # February 2026 has 28 days.
    assert next_instance.due_date == "2026-02-28"


def test_expand_recurring_todo_is_idempotent(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(title="Daily thing", due_date="2026-09-30", recurrence_rule="FREQ=DAILY"),
    )
    first = handlers.expand_recurring_todo(conn, template.id)
    second = handlers.expand_recurring_todo(conn, template.id)
    assert first.id == second.id

    all_todos = handlers.list_todos(conn, status="all", limit=100)
    matching = [t for t in all_todos if t.parent_todo_id == template.id]
    assert len(matching) == 1


def test_expand_recurring_todo_returns_none_without_recurrence_rule(conn):
    template = handlers.add_todo(conn, TodoCreate(title="No recurrence"))
    assert handlers.expand_recurring_todo(conn, template.id) is None


def test_expand_recurring_todo_returns_none_for_missing_todo(conn):
    assert handlers.expand_recurring_todo(conn, 999999) is None


def test_complete_todo_auto_invokes_expansion(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(title="Auto expand", due_date="2026-09-30", recurrence_rule="FREQ=DAILY"),
    )
    handlers.complete_todo(conn, template.id)

    all_todos = handlers.list_todos(conn, status="all", limit=100)
    children = [t for t in all_todos if t.parent_todo_id == template.id]
    assert len(children) == 1
    assert children[0].due_date == "2026-10-01"
    assert children[0].is_completed is False


def test_complete_todo_without_recurrence_does_not_create_instance(conn):
    template = handlers.add_todo(conn, TodoCreate(title="One-off"))
    handlers.complete_todo(conn, template.id)

    all_todos = handlers.list_todos(conn, status="all", limit=100)
    children = [t for t in all_todos if t.parent_todo_id == template.id]
    assert children == []


def test_expand_recurring_todo_inherits_goal_and_jira_ref(conn):
    template = handlers.add_todo(
        conn,
        TodoCreate(
            title="Linked recurring",
            due_date="2026-09-30",
            recurrence_rule="FREQ=DAILY",
            goal_id=9,
            jira_ref="CXP-400",
        ),
    )
    next_instance = handlers.expand_recurring_todo(conn, template.id)
    assert next_instance.goal_id == 9
    assert next_instance.jira_ref == "CXP-400"


def test_unsupported_recurrence_rule_raises(conn):
    template = handlers.add_todo(
        conn, TodoCreate(title="Bad rule", recurrence_rule="FREQ=YEARLY")
    )
    with pytest.raises(ValueError):
        handlers.expand_recurring_todo(conn, template.id)
