"""Terminal pretty-printing helpers for sb CLI output."""

from __future__ import annotations

import json
from typing import Any


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def print_log_result(result: dict, *, quiet: bool = False) -> None:
    if quiet:
        return
    if result.get("was_new") is False:
        print(f"already recorded: ledger id {result['id']} (ts {result['ts']})")
        return
    suffix = " (written to CHANGELOG.md)" if result.get("persisted_to_file") else ""
    print(f"ledger id {result['id']} at {result['ts']}{suffix}")


def print_entries(entries: list[dict], *, quiet: bool = False) -> None:
    if quiet:
        return
    if not entries:
        print("(no entries)")
        return
    for entry in entries:
        scope = f" — {entry['scope']}" if entry.get("scope") else ""
        print(f"[{entry.get('id')}] {entry.get('ts')} {entry.get('action_verb')} {entry.get('summary')}{scope}")


def print_projects(projects: list[dict], *, quiet: bool = False) -> None:
    if quiet:
        return
    if not projects:
        print("(no projects enrolled)")
        return
    for project in projects:
        print(
            f"{project['project']}: {project['root_path']} "
            f"({project['sync_mode']}) -> {project['changelog_path']}"
        )
