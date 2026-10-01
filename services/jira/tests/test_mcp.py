import asyncio
from unittest.mock import patch

from sb_jira import file_store, mcp_tools, tracking


def test_all_four_tools_registered():
    tools = asyncio.run(mcp_tools.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "list_jira_tickets",
        "get_jira_ticket",
        "sync_jira",
        "jira_status",
        "track_jira",
        "untrack_jira",
    }


def test_list_jira_tickets_matches_file_store():
    result = mcp_tools.list_jira_tickets()
    expected_keys = {t.key for t in file_store.load_all()}
    result_keys = {t["key"] for t in result}
    assert result_keys == expected_keys
    assert len(result) == 2  # CXP-46855, CXP-40585 fixtures


def test_list_marks_locally_tracked_tickets():
    from sb_jira.config import settings

    tracking.add_key("CXP-46855", settings.tracked_path)
    by_key = {row["key"]: row for row in mcp_tools.list_jira_tickets()}
    assert by_key["CXP-46855"]["tracked"] is True
    assert by_key["CXP-40585"]["tracked"] is False


def test_list_jira_tickets_filters_by_status():
    result = mcp_tools.list_jira_tickets(status="Code Review")
    assert all(t["status"] == "Code Review" for t in result)
    assert any(t["key"] == "CXP-46855" for t in result)


def test_list_jira_tickets_filters_by_q():
    result = mcp_tools.list_jira_tickets(q="notification")
    keys = {t["key"] for t in result}
    assert keys == {"CXP-46855"}


def test_hide_closed_and_project_list():
    from sb_jira.models import JiraTicket, Person

    def ticket(key: str, status: str) -> JiraTicket:
        return JiraTicket(
            key=key,
            project=key.split("-")[0],
            title=key,
            status=status,
            priority="Medium",
            issue_type="Task",
            assignee=Person(name="Ada", email="ada@example.com"),
            created="2026-09-01",
            updated="2026-09-30",
            url=f"https://cisco-cxe.atlassian.net/browse/{key}",
        )

    rows = [
        ticket("CXP-1", "Open"),
        ticket("CXPL-2", "Closed"),
        ticket("FSRE-3", "Done"),
        ticket("FSRE-4", "In Progress"),
    ]
    hidden = file_store.apply_filters(rows, hide_closed=True)
    assert [item.key for item in hidden] == ["CXP-1", "FSRE-4"]
    selected = file_store.apply_filters(rows, projects=["FSRE", "CXPL"])
    assert [item.key for item in selected] == ["CXPL-2", "FSRE-3", "FSRE-4"]


def test_list_jira_tickets_respects_limit():
    result = mcp_tools.list_jira_tickets(limit=1)
    assert len(result) == 1
    assert result[0]["key"] == "CXP-46855"  # updated 2026-08-19, newer than CXP-40585


def test_jira_status_reads_newest_history_date():
    from sb_jira.config import settings

    settings.tickethistory_path.write_text(
        "| 2026-09-30 | CXP-53812 | **Status Update** | still open |\n"
        "| 2026-09-08 | CXP-1 | **Removed** | closed |\n",
        encoding="utf-8",
    )
    assert mcp_tools.jira_status()["last_sync_at"] == "2026-09-30"


def test_get_jira_ticket_real_fixture():
    result = mcp_tools.get_jira_ticket("CXP-46855")
    assert result is not None
    assert result["key"] == "CXP-46855"
    assert "sections" in result
    assert "description_md" in result


def test_get_jira_ticket_missing_returns_none():
    assert mcp_tools.get_jira_ticket("CXP-00000") is None


def test_sync_jira_no_token_returns_error():
    with patch("sb_jira.atlassian_client.get_token", return_value=None):
        result = mcp_tools.sync_jira()
    assert result["errors"]
    assert "No Atlassian token" in result["errors"][0]
    assert result["updated_count"] == 0
    assert result["added_count"] == 0


# ---------------------------------------------------------------------------
# sync_jira — soft lock + record_sync bridge wiring (phase 2j)
# ---------------------------------------------------------------------------


def test_sync_jira_calls_record_sync_with_counts(monkeypatch):
    calls = []
    monkeypatch.setattr(
        mcp_tools,
        "record_sync",
        lambda adapter, counts, errors=None: calls.append((adapter, counts, errors)),
    )

    with patch("sb_jira.atlassian_client.get_token", return_value=None):
        result = mcp_tools.sync_jira()

    assert len(calls) == 1
    adapter, counts, errors = calls[0]
    assert adapter == "jira"
    assert counts == {"updated_count": 0, "added_count": 0, "unchanged_count": 0}
    assert errors and "No Atlassian token" in errors[0]
    assert result["errors"]


def test_sync_jira_already_running_returns_stub_and_does_not_sync(monkeypatch):
    from contextlib import contextmanager

    @contextmanager
    def _fake_lock(name):
        yield False

    monkeypatch.setattr(mcp_tools, "sync_lock", _fake_lock)

    calls = []
    monkeypatch.setattr(mcp_tools, "record_sync", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(
        mcp_tools.sync,
        "run_sync",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not sync")),
    )

    result = mcp_tools.sync_jira()
    assert result["status"] == "already_running"
    assert result["updated_count"] == 0
    assert calls == []


def test_jira_status_shape():
    result = mcp_tools.jira_status()
    assert set(result.keys()) == {
        "atlassian_reachable",
        "atlassian_error",
        "tickets_count",
        "tracked_count",
        "last_sync_at",
    }
    assert result["tickets_count"] == 2
