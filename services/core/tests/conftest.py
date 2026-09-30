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
