"""URL classifier MCP tool: turn a pasted URL into a kind + extracted fields
+ a suggested next action, for one-click triage of pasted links.

Read-only and side-effect free: it never calls any of the suggested
actions itself.
"""

from __future__ import annotations

import re

from fastmcp import FastMCP

mcp = FastMCP(
    "sb-url-hints",
    instructions=(
        "Classify a pasted URL and suggest a next action. Never performs "
        "the suggested action itself."
    ),
)

_JIRA_RE = re.compile(
    r"^https?://(?P<site>[^/]+)/browse/(?P<key>[A-Z][A-Z0-9]*-\d+)/?$"
)
_WEBEX_APP_RE = re.compile(r"^webexteams://im\?space=(?P<space_id>[^&]+)")
_WEBEX_WEB_RE = re.compile(
    r"^https?://web\.webex\.com/space/(?P<space_id>[^/?#]+)"
)
_GITHUB_PR_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<pr_number>\d+)"
)
_FILE_RE = re.compile(r"^file://(?P<path>/.*)$")


@mcp.tool()
def parse_url_hint(url: str) -> dict:
    """Classify a pasted URL. Returns ``{kind, extracted, suggested_action}``.

    Recognized kinds: ``jira`` (Atlassian browse link -> ``track_jira``),
    ``webex`` (app deep link or web space link -> ``open_space``), ``github``
    (pull request link -> ``attach_as_ref``), ``file`` (``file://`` URI ->
    ``attach_as_ref``). Anything else falls back to ``kind="generic"`` with
    ``suggested_action="attach_as_ref"``.
    """
    clean = (url or "").strip()

    match = _JIRA_RE.match(clean)
    if match:
        return {
            "kind": "jira",
            "extracted": {"key": match.group("key"), "site": match.group("site")},
            "suggested_action": "track_jira",
        }

    match = _WEBEX_APP_RE.match(clean)
    if match:
        return {
            "kind": "webex",
            "extracted": {"space_id": match.group("space_id")},
            "suggested_action": "open_space",
        }

    match = _WEBEX_WEB_RE.match(clean)
    if match:
        return {
            "kind": "webex",
            "extracted": {"space_id": match.group("space_id"), "url": clean},
            "suggested_action": "open_space",
        }

    match = _GITHUB_PR_RE.match(clean)
    if match:
        return {
            "kind": "github",
            "extracted": {
                "repo": f"{match.group('owner')}/{match.group('repo')}",
                "pr_number": int(match.group("pr_number")),
            },
            "suggested_action": "attach_as_ref",
        }

    match = _FILE_RE.match(clean)
    if match:
        return {
            "kind": "file",
            "extracted": {"path": match.group("path")},
            "suggested_action": "attach_as_ref",
        }

    return {"kind": "generic", "extracted": {"url": clean}, "suggested_action": "attach_as_ref"}
