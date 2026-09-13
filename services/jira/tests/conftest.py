import shutil
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture()
def tmp_tickets_dir(tmp_path: Path) -> Path:
    """Copy fixture ticket files into an isolated temp directory."""
    dest = tmp_path / "tickets"
    dest.mkdir(exist_ok=True)
    for f in FIXTURES_DIR.glob("*.md"):
        shutil.copy(f, dest / f.name)
    return dest


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """Point sb_jira.config.settings at a scratch directory for every test,
    so tests never touch the real ciq/docs/jira mirror."""
    from sb_jira.config import settings

    tickets_dir = tmp_path / "tickets"
    tickets_dir.mkdir(exist_ok=True)
    for f in FIXTURES_DIR.glob("*.md"):
        shutil.copy(f, tickets_dir / f.name)

    readme = tmp_path / "README.md"
    history = tmp_path / "tickethistory.md"

    monkeypatch.setattr(settings, "tickets_dir", tickets_dir)
    monkeypatch.setattr(settings, "readme_path", readme)
    monkeypatch.setattr(settings, "tickethistory_path", history)
    yield settings
