from pathlib import Path

from sb_jira import file_store


def test_parse_cxp_46855(fixtures_dir: Path):
    ticket = file_store.load(fixtures_dir / "CXP-46855.md")

    assert ticket.key == "CXP-46855"
    assert ticket.project == "CXP"
    assert "notification" in ticket.title.lower()
    assert ticket.status == "Code Review"
    assert ticket.priority == "Medium"
    assert ticket.issue_type == "Story"
    assert ticket.assignee.name == "PRASAD P R"
    assert ticket.assignee.email == "praspr@cisco.com"
    assert ticket.reporter is not None
    assert ticket.reporter.name == "PRASAD P R"
    assert ticket.created == "2026-08-07"
    assert ticket.updated == "2026-08-19"
    assert "Q1FY27-EC-Assessments-App-Configuration-tracker" in ticket.labels
    assert ticket.url == "https://cisco-cxe.atlassian.net/browse/CXP-46855"
    assert ticket.description
    assert len(ticket.description) <= 201
    assert ticket.description_md
    section_names = [s.name for s in ticket.sections]
    assert "Context" in section_names
    assert "Feature Description / Requirements" in section_names
    assert "Notes" in section_names


def test_parse_cxp_40585(fixtures_dir: Path):
    ticket = file_store.load(fixtures_dir / "CXP-40585.md")

    assert ticket.key == "CXP-40585"
    assert ticket.status == "In Testing"
    assert ticket.issue_type == "Bug"
    assert ticket.reporter is not None
    assert ticket.reporter.name == "Babu R"
    assert "Performance" in ticket.labels
    assert ticket.assignee.name == "PRASAD P R"


def test_load_all_isolates_bad_files(tmp_tickets_dir: Path):
    bad = tmp_tickets_dir / "BROKEN.md"
    bad.write_text("not a valid ticket file at all", encoding="utf-8")

    tickets = file_store.load_all(tmp_tickets_dir)
    keys = {t.key for t in tickets}
    assert "CXP-46855" in keys
    assert "CXP-40585" in keys
    # BROKEN.md should be skipped, not crash the whole load
    assert len(tickets) == 2
