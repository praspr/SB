import os
import tempfile
from pathlib import Path

_TEST_STORAGE = tempfile.TemporaryDirectory()
_ROOT = Path(_TEST_STORAGE.name)
(_ROOT / "tickets").mkdir()

os.environ["SB_TODOS_DB_PATH"] = str(_ROOT / "todos.db")
os.environ["SB_JIRA_TICKETS_DIR"] = str(_ROOT / "tickets")
os.environ["SB_JIRA_README_PATH"] = str(_ROOT / "README.md")
os.environ["SB_JIRA_TICKETHISTORY_PATH"] = str(_ROOT / "tickethistory.md")
os.environ["SB_CORE_DB_PATH"] = str(_ROOT / "core.db")

# Guard against sb_core.config.seed_registry_if_empty (triggered by any
# TestClient(app) lifespan startup in this session) seeding a "sb" ->
# project row whose changelog_path is the real developer's repo
# CHANGELOG.md (see _SEED_PROJECTS -- those paths are intentionally
# hardcoded to the real machine for production first-boot). Any later
# test in this session that logs to the ledger for project="sb" without
# explicitly monkeypatching ledger_tools._get_conn away from the shared
# session DB would otherwise dual-sync a bullet into that real file.
# Pre-seeding one harmless row here makes sb_project_registry non-empty
# up front, so seed_registry_if_empty's "only seed when empty" guard
# short-circuits for the rest of the session.
from sb_core.store.db import connect as _connect  # noqa: E402
from sb_core.store.ledger import register_project as _register_project  # noqa: E402

_guard_conn = _connect(_ROOT / "core.db")
try:
    _register_project(
        _guard_conn,
        project="__test_session_guard__",
        root_path=str(_ROOT),
        changelog_path=str(_ROOT / "CHANGELOG.md"),
        sync_mode="sqlite-only",
    )
finally:
    _guard_conn.close()
