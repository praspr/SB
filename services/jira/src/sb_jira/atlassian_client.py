"""Read-only Atlassian JIRA REST v3 client.

Auth: HTTP Basic (email + API token). Token is read from the OS keyring
(service="sb", username="jira.token") with an environment variable fallback.

Never performs write operations against Atlassian.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import settings
from .models import JiraTicketDetail, Person, Section

logger = logging.getLogger("sb_jira.atlassian_client")

FIELDS = "summary,status,priority,assignee,reporter,updated,created,labels,fixVersions,description,issuetype"


class AtlassianAuthError(Exception):
    pass


class AtlassianClientError(Exception):
    pass


def get_token() -> str | None:
    """Read the Atlassian API token from keyring, falling back to env var."""
    try:
        import keyring

        token = keyring.get_password(settings.keyring_service, settings.keyring_username)
        if token:
            return token
    except Exception as exc:  # noqa: BLE001
        logger.debug("keyring lookup failed: %s", exc)

    import os

    return os.environ.get("ATLASSIAN_API_TOKEN")


def _auth_header(email: str, token: str) -> dict[str, str]:
    raw = f"{email}:{token}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}


def _adf_to_text(node: Any) -> str:
    """Recursively extract plain text from an Atlassian Document Format node."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_adf_to_text(n) for n in node)
    if isinstance(node, dict):
        parts: list[str] = []
        node_type = node.get("type")
        if node_type == "text":
            parts.append(node.get("text", ""))
        content = node.get("content")
        if content:
            parts.append(_adf_to_text(content))
        if node_type in {"paragraph", "heading", "blockquote"}:
            parts.append("\n")
        return "".join(parts)
    return ""


def probe_reachable(timeout: float = 5.0) -> tuple[bool, str | None]:
    """Cheap reachability + auth probe. Returns (reachable, error_message)."""
    token = get_token()
    if not token:
        return False, "No Atlassian token — run `sb secret set jira.token`"
    url = f"{settings.atlassian_site}/rest/api/3/myself"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=_auth_header(settings.atlassian_email, token))
        if resp.status_code == 200:
            return True, None
        if resp.status_code == 401:
            return False, "Atlassian authentication failed (401)"
        return False, f"Atlassian returned HTTP {resp.status_code}"
    except httpx.HTTPError as exc:
        return False, f"Atlassian unreachable: {exc}"


def _issue_to_detail(issue: dict[str, Any]) -> JiraTicketDetail:
    key = issue["key"]
    fields = issue.get("fields", {})
    project = key.split("-")[0]

    status = (fields.get("status") or {}).get("name", "Open")
    priority = (fields.get("priority") or {}).get("name", "Medium")
    issue_type = (fields.get("issuetype") or {}).get("name", "Task")
    title = fields.get("summary", "")

    assignee_raw = fields.get("assignee") or {}
    assignee = Person(
        name=assignee_raw.get("displayName", "Unassigned"),
        email=assignee_raw.get("emailAddress", ""),
    )

    reporter_raw = fields.get("reporter")
    reporter = None
    if reporter_raw:
        reporter = Person(
            name=reporter_raw.get("displayName", ""),
            email=reporter_raw.get("emailAddress", ""),
        )

    created = fields.get("created", "")
    updated = fields.get("updated", "")

    labels = fields.get("labels", []) or []
    fix_versions = [fv.get("name", "") for fv in (fields.get("fixVersions") or [])]

    description_adf = fields.get("description")
    description_md = _adf_to_text(description_adf).strip() if description_adf else ""
    description = (description_md[:200] + "…") if len(description_md) > 200 else description_md

    url = f"{settings.atlassian_site}/browse/{key}"

    return JiraTicketDetail(
        key=key,
        project=project,
        title=title,
        status=status,
        priority=priority,
        issue_type=issue_type,
        assignee=assignee,
        reporter=reporter,
        created=created,
        updated=updated,
        labels=labels,
        fix_versions=fix_versions,
        description=description,
        url=url,
        file_path="",
        description_md=description_md,
        sections=[Section(name="Context", body=description_md)] if description_md else [],
    )


def fetch_all_assigned(timeout: float = 15.0) -> list[JiraTicketDetail]:
    """Fetch all tickets matching `settings.atlassian_jql` via REST v3, paginated."""
    token = get_token()
    if not token:
        raise AtlassianAuthError("No Atlassian token configured")

    headers = _auth_header(settings.atlassian_email, token)
    url = f"{settings.atlassian_site}/rest/api/3/search"
    start_at = 0
    max_results = 100
    tickets: list[JiraTicketDetail] = []

    with httpx.Client(timeout=timeout) as client:
        while True:
            resp = client.get(
                url,
                headers=headers,
                params={
                    "jql": settings.atlassian_jql,
                    "fields": FIELDS,
                    "startAt": start_at,
                    "maxResults": max_results,
                },
            )
            if resp.status_code == 401:
                raise AtlassianAuthError("Atlassian authentication failed (401)")
            if resp.status_code != 200:
                raise AtlassianClientError(f"Atlassian search failed: HTTP {resp.status_code} {resp.text[:300]}")

            data = resp.json()
            issues = data.get("issues", [])
            for issue in issues:
                try:
                    tickets.append(_issue_to_detail(issue))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("failed to parse Atlassian issue %s: %s", issue.get("key"), exc)

            total = data.get("total", len(issues))
            start_at += len(issues)
            if start_at >= total or not issues:
                break

    return tickets


def last_updated_utc(tickets: list[JiraTicketDetail]) -> str:
    """Best-effort 'now' UTC timestamp string for the history row."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
