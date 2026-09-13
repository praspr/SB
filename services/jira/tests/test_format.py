from pathlib import Path

from sb_jira import file_store, format


def test_roundtrip_cxp_46855(fixtures_dir: Path):
    ticket = file_store.load(fixtures_dir / "CXP-46855.md")
    written = format.to_markdown(ticket)
    reparsed = file_store.parse_str(written, file_path=ticket.file_path)

    assert reparsed.key == ticket.key
    assert reparsed.title == ticket.title
    assert reparsed.status == ticket.status
    assert reparsed.priority == ticket.priority
    assert reparsed.issue_type == ticket.issue_type
    assert reparsed.assignee.name == ticket.assignee.name
    assert reparsed.labels == ticket.labels
    assert reparsed.created == ticket.created
    assert reparsed.updated == ticket.updated
    assert reparsed.url == ticket.url

    section_names_before = {s.name for s in ticket.sections}
    section_names_after = {s.name for s in reparsed.sections}
    assert section_names_before == section_names_after


def test_roundtrip_cxp_40585(fixtures_dir: Path):
    ticket = file_store.load(fixtures_dir / "CXP-40585.md")
    written = format.to_markdown(ticket)
    reparsed = file_store.parse_str(written, file_path=ticket.file_path)

    assert reparsed.key == ticket.key
    assert reparsed.title == ticket.title
    assert reparsed.status == ticket.status
    assert reparsed.reporter is not None
    assert reparsed.reporter.name == ticket.reporter.name
