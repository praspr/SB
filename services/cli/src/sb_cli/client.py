"""Thin MCP JSON-RPC/Streamable HTTP client for the sb CLI.

Talks directly to sb-core's ``/mcp`` endpoint. No authentication is used
(sb-core binds to 127.0.0.1 only). Mirrors the wire-protocol handling in
``sb_webex.client.McpClient`` (initialize -> initialized notification ->
tools/call), trimmed to what the CLI needs.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

DEFAULT_ENDPOINT = "http://127.0.0.1:8787/mcp"
_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_INFO = {"name": "sb-cli", "version": "0.1.0"}


class McpTransportError(RuntimeError):
    """Raised when the MCP endpoint cannot be reached or errors at transport level."""


class McpToolError(RuntimeError):
    """Raised when the MCP server returns a JSON-RPC error for a tool call."""


class McpClient:
    """Minimal Streamable HTTP MCP client (no auth; local-only sb-core)."""

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, *, timeout: float = 30.0) -> None:
        self._endpoint = endpoint
        self._timeout = timeout
        self._session: Optional[str] = None
        self._initialized = False

    def _rpc(self, method: str, params: Optional[dict] = None, *, notify: bool = False) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = 1
        if params is not None:
            body["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session

        try:
            response = httpx.post(
                self._endpoint, headers=headers, json=body, timeout=self._timeout
            )
        except httpx.HTTPError as exc:
            raise McpTransportError(
                f"could not reach sb-core at {self._endpoint}: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise McpTransportError(
                f"sb-core returned HTTP {response.status_code} for {method}"
            )

        self._session = response.headers.get("mcp-session-id") or self._session
        text = response.text.strip()
        if not text:
            return None

        if text.startswith("{"):
            message = response.json()
        else:
            data_lines = [
                line.split(":", 1)[1].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            ]
            if not data_lines:
                return None
            message = json.loads(data_lines[-1])

        if isinstance(message, dict) and message.get("error"):
            err = message["error"]
            raise McpToolError(str(err.get("message") or "sb-core MCP error"))
        return None if notify else message.get("result")

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": _CLIENT_INFO,
            },
        )
        self._rpc("notifications/initialized", notify=True)
        self._initialized = True

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        """Call an MCP tool by name and return its decoded result payload."""
        self._ensure_initialized()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}}) or {}

        structured = result.get("structuredContent")
        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]
        if structured is not None:
            return structured

        content = result.get("content") or []
        if content and isinstance(content[0], dict) and content[0].get("text"):
            raw_text = content[0]["text"]
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                return {"text": raw_text}
        return {}
