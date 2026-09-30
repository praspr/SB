"""Write-capable Webex MCP wrapper for explicit message posting only."""

from __future__ import annotations

from fastmcp import FastMCP

from sb_webex.client import McpClient, WebexAuthError, access_token

mcp = FastMCP(
    "sb-webex-post",
    instructions=(
        "Post one explicit message to Webex through the hosted MCP. Never reads or "
        "syncs; only posts when the caller asks directly."
    ),
)


@mcp.tool()
def webex_post_message(
    space_id: str,
    markdown: str,
    message_type: str = "text",
) -> dict:
    """Post one message to a Webex space through the hosted MCP."""
    token = access_token()
    if not token:
        return {
            "posted": False,
            "space_id": space_id,
            "message_type": message_type,
            "error": "Webex is not signed in. Open /webex/login.",
        }

    try:
        payload = McpClient(token).call_tool(
            "post_webex_message",
            {
                "space_id": space_id,
                "markdown": markdown,
                "message_type": message_type,
            },
        )
    except WebexAuthError as exc:
        return {
            "posted": False,
            "space_id": space_id,
            "message_type": message_type,
            "error": str(exc),
        }

    return {
        "posted": True,
        "space_id": space_id,
        "message_type": message_type,
        "result": payload,
    }
