"""Read-only discovery of installed SKILL.md files from allow-listed roots."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

MAX_SKILL_BYTES = 256 * 1024
MAX_PROCEDURE_CHARS = 32_000
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,64}$")
_TOOL_RE = re.compile(r"^- `([a-z][a-z0-9_]*)`$", re.MULTILINE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_roots() -> list[tuple[str, Path]]:
    """Explicit roots only. Never walks the rest of the home directory."""
    root = repo_root()
    home = Path.home()
    candidates: list[tuple[str, Path]] = [
        ("project", root / "harness" / "skills"),
        ("project", root / ".cursor" / "skills"),
        ("cursor", home / ".cursor" / "skills"),
        ("claude", home / ".claude" / "skills"),
    ]
    for extra in settings.extra_skill_roots:
        candidates.append(("configured", Path(extra).expanduser()))
    return [
        (source, path)
        for source, path in candidates
        if path.is_dir() and not path.is_symlink()
    ]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def _skill_files(root: Path) -> list[tuple[str, Path]]:
    """Return (id, SKILL.md) pairs that stay inside *root*."""
    try:
        root_real = root.resolve(strict=True)
    except OSError:
        return []
    found: list[tuple[str, Path]] = []
    try:
        children = sorted(root_real.iterdir(), key=lambda item: item.name)
    except OSError:
        return []
    for child in children:
        if child.is_symlink() and not _inside(root_real, child):
            continue
        directory = child.resolve(strict=False)
        if not _inside(root_real, directory) or not directory.is_dir():
            continue
        skill_id = child.name
        if not _ID_RE.match(skill_id):
            continue
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            continue
        if not _inside(root_real, skill_file):
            continue
        found.append((skill_id, skill_file))
    return found


def _parse(text: str) -> tuple[str, str, list[str], str] | None:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return None
    raw, procedure = text[4:].split("\n---\n", 1)
    name = ""
    description = ""
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            return None
        if key.strip() == "name":
            name = value.strip().strip("\"'")
        elif key.strip() == "description":
            description = value.strip().strip("\"'")
    if not description:
        return None
    match = re.search(
        r"^## Allowed tools\n(?P<body>.*?)(?=^## |\Z)",
        procedure,
        flags=re.MULTILINE | re.DOTALL,
    )
    tools = _TOOL_RE.findall(match.group("body")) if match else []
    bounded = procedure.strip()
    if len(bounded) > MAX_PROCEDURE_CHARS:
        bounded = bounded[:MAX_PROCEDURE_CHARS] + "\n\n[truncated]\n"
    return name, description, tools, bounded


def sync_skills(conn, roots: list[tuple[str, Path]] | None = None) -> dict[str, int]:
    """Rescan allow-listed roots. Missing skills stay in the table, unavailable."""
    chosen = default_roots() if roots is None else roots
    seen: dict[str, dict] = {}
    duplicates = 0
    now = _utcnow()

    for source, root in chosen:
        if not root.exists() or root.is_symlink() or not root.is_dir():
            continue
        for skill_id, path in _skill_files(root):
            if skill_id in seen:
                duplicates += 1
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            modified = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            if size > MAX_SKILL_BYTES:
                seen[skill_id] = {
                    "id": skill_id,
                    "name": skill_id,
                    "description": "Skill file exceeds the size cap and was not indexed.",
                    "source": source,
                    "path": str(path),
                    "content_sha256": "",
                    "modified_at": modified,
                    "available": 0,
                    "allowed_tools": "[]",
                    "procedure": "",
                }
                continue
            raw = path.read_bytes()
            parsed = _parse(raw.decode("utf-8", errors="replace"))
            if parsed is None:
                seen[skill_id] = {
                    "id": skill_id,
                    "name": skill_id,
                    "description": "Skill frontmatter could not be parsed.",
                    "source": source,
                    "path": str(path),
                    "content_sha256": _sha256(raw),
                    "modified_at": modified,
                    "available": 0,
                    "allowed_tools": "[]",
                    "procedure": "",
                }
                continue
            name, description, tools, procedure = parsed
            seen[skill_id] = {
                "id": skill_id,
                "name": name or skill_id,
                "description": description,
                "source": source,
                "path": str(path),
                "content_sha256": _sha256(raw),
                "modified_at": modified,
                "available": 1,
                "allowed_tools": json.dumps(tools),
                "procedure": procedure,
            }

    added = 0
    updated = 0
    for row in seen.values():
        existing = conn.execute(
            "SELECT content_sha256, available FROM sb_skills WHERE id = ?",
            (row["id"],),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO sb_skills (
              id, name, description, source, path, content_sha256, modified_at,
              synced_at, enabled, available, allowed_tools, procedure
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              description = excluded.description,
              source = excluded.source,
              path = excluded.path,
              content_sha256 = excluded.content_sha256,
              modified_at = excluded.modified_at,
              synced_at = excluded.synced_at,
              available = excluded.available,
              allowed_tools = excluded.allowed_tools,
              procedure = excluded.procedure
            """,
            (
                row["id"],
                row["name"],
                row["description"],
                row["source"],
                row["path"],
                row["content_sha256"],
                row["modified_at"],
                now,
                row["available"],
                row["allowed_tools"],
                row["procedure"],
            ),
        )
        if existing is None:
            added += 1
        elif (
            existing["content_sha256"] != row["content_sha256"]
            or int(existing["available"]) != row["available"]
        ):
            updated += 1

    unavailable = 0
    if seen:
        placeholders = ",".join("?" for _ in seen)
        stale = conn.execute(
            f"SELECT id FROM sb_skills WHERE available = 1 AND id NOT IN ({placeholders})",
            tuple(seen),
        ).fetchall()
    else:
        stale = conn.execute("SELECT id FROM sb_skills WHERE available = 1").fetchall()
    if stale:
        ids = [row["id"] for row in stale]
        conn.execute(
            f"UPDATE sb_skills SET available = 0, synced_at = ? WHERE id IN ({','.join('?' for _ in ids)})",
            (now, *ids),
        )
        unavailable = len(ids)
    conn.commit()
    return {
        "added": added,
        "updated": updated,
        "unavailable": unavailable,
        "duplicates": duplicates,
    }


def list_skills(
    conn,
    source: str | None = None,
    status: str | None = None,
    query: str | None = None,
) -> list[dict]:
    sql = "SELECT id, name, description, source, path, content_sha256, modified_at, synced_at, enabled, available, allowed_tools FROM sb_skills WHERE 1=1"
    params: list = []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if status == "available":
        sql += " AND available = 1"
    elif status == "unavailable":
        sql += " AND available = 0"
    if query:
        sql += " AND (id LIKE ? OR name LIKE ? OR description LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])
    sql += " ORDER BY name"
    rows = []
    for row in conn.execute(sql, params).fetchall():
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["available"] = bool(item["available"])
        item["allowed_tools"] = json.loads(item["allowed_tools"] or "[]")
        item.pop("path", None)
        rows.append(item)
    return rows


def get_skill(conn, skill_id: str) -> dict | None:
    if not _ID_RE.match(skill_id):
        return None
    row = conn.execute("SELECT * FROM sb_skills WHERE id = ?", (skill_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["enabled"] = bool(item["enabled"])
    item["available"] = bool(item["available"])
    item["allowed_tools"] = json.loads(item["allowed_tools"] or "[]")
    # The canonical path is an absolute local path. Return only the file name.
    item["path"] = Path(item["path"]).name
    return item


def enabled_skills(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT id, name, description, procedure
        FROM sb_skills
        WHERE enabled = 1 AND available = 1
        ORDER BY id
        """).fetchall()
    return [dict(row) for row in rows]


_REGISTERED: set[str] = set()


def refresh_skill_surface(mcp, conn) -> None:
    """Expose enabled, available skills as prompts and resources."""
    from fastmcp.prompts import Prompt
    from fastmcp.resources import Resource

    from .store.db import connect

    wanted = {row["id"]: row for row in enabled_skills(conn)}
    dropped = _REGISTERED - set(wanted)
    if dropped:
        names = {f"skill_{skill_id}" for skill_id in dropped}
        uris = {f"skill://{skill_id}" for skill_id in dropped}
        mcp.disable(names=names | uris, components={"prompt", "resource"})
    for skill_id, row in wanted.items():
        if skill_id not in _REGISTERED:

            def _procedure(_skill_id: str = skill_id) -> str:
                owned = connect(settings.db_path)
                try:
                    found = get_skill(owned, _skill_id)
                    return "" if found is None else str(found.get("procedure") or "")
                finally:
                    owned.close()

            mcp.add_prompt(
                Prompt.from_function(
                    _procedure,
                    name=f"skill_{skill_id}",
                    description=row["description"],
                )
            )
            mcp.add_resource(
                Resource.from_function(
                    _procedure,
                    uri=f"skill://{skill_id}",
                    name=f"skill_{skill_id}",
                    description=row["description"],
                    mime_type="text/markdown",
                )
            )
            _REGISTERED.add(skill_id)
        else:
            mcp.enable(
                names={f"skill_{skill_id}", f"skill://{skill_id}"},
                components={"prompt", "resource"},
            )


def register_skill_tools(mcp) -> None:
    """Register skill tools on the parent server."""
    from .store.db import connect

    def sync_skills_tool() -> dict[str, int]:
        """Rescan allow-listed skill roots and return added, updated, and unavailable counts."""
        conn = connect(settings.db_path)
        try:
            result = sync_skills(conn)
            refresh_skill_surface(mcp, conn)
            return result
        finally:
            conn.close()

    def list_skills_tool(
        source: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        """List indexed skills. status is available, unavailable, or omitted for all."""
        conn = connect(settings.db_path)
        try:
            return list_skills(conn, source=source, status=status, query=query)
        finally:
            conn.close()

    def get_skill_tool(skill_id: str) -> dict | None:
        """Return one skill's metadata and bounded procedure markdown."""
        conn = connect(settings.db_path)
        try:
            return get_skill(conn, skill_id)
        finally:
            conn.close()

    mcp.tool(name="sync_skills")(sync_skills_tool)
    mcp.tool(name="list_skills")(list_skills_tool)
    mcp.tool(name="get_skill")(get_skill_tool)
