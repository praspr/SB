from unittest.mock import patch

from fastapi.testclient import TestClient

from sb_jira.main import app
from sb_jira.models import JiraTicketDetail, Person, Section


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["tickets_on_disk"] == 2


def test_list_tickets():
    client = TestClient(app)
    resp = client.get("/api/jira/tickets")
    assert resp.status_code == 200
    tickets = resp.json()
    assert len(tickets) == 2
    keys = {t["key"] for t in tickets}
    assert keys == {"CXP-46855", "CXP-40585"}
    for t in tickets:
        assert "assignee" in t
        assert "url" in t
        assert "labels" in t


def test_get_ticket_detail():
    client = TestClient(app)
    resp = client.get("/api/jira/tickets/CXP-46855")
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == "CXP-46855"
    assert "sections" in body
    assert "description_md" in body


def test_get_ticket_not_found():
    client = TestClient(app)
    resp = client.get("/api/jira/tickets/CXP-99999")
    assert resp.status_code == 404


def test_status():
    client = TestClient(app)
    resp = client.get("/api/jira/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tickets_count"] == 2
    assert "atlassian_reachable" in body


def test_sync_no_token_returns_200_with_errors():
    client = TestClient(app)
    with patch("sb_jira.atlassian_client.get_token", return_value=None):
        resp = client.post("/api/jira/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"]


def test_sync_with_mocked_atlassian_adds_new_ticket():
    fake_ticket = JiraTicketDetail(
        key="CXP-99999",
        project="CXP",
        title="Mocked new ticket",
        status="Open",
        priority="Medium",
        issue_type="Bug",
        assignee=Person(name="PRASAD P R", email="praspr@cisco.com"),
        reporter=None,
        created="2026-09-01",
        updated="2026-09-10",
        labels=["mock"],
        fix_versions=[],
        description="Mocked",
        url="https://cisco-cxe.atlassian.net/browse/CXP-99999",
        file_path="",
        description_md="Mocked description body.",
        sections=[Section(name="Context", body="Mocked description body.")],
    )

    client = TestClient(app)
    with patch("sb_jira.sync.atlassian_client.fetch_all_assigned", return_value=[fake_ticket]), patch(
        "sb_jira.sync.atlassian_client.last_updated_utc", return_value="2026-09-10 00:00:00 UTC"
    ):
        resp = client.post("/api/jira/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert not body["errors"]
    assert body["added_count"] == 1
    assert body["history_row_appended"] is True

    # Confirm it now shows up in the listing.
    resp2 = client.get("/api/jira/tickets")
    keys = {t["key"] for t in resp2.json()}
    assert "CXP-99999" in keys
