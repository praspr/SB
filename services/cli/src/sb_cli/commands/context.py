"""`sb context` — recent entries, open threads, and tracked refs for a project."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone

from ..client import DEFAULT_ENDPOINT, McpClient, McpToolError, McpTransportError
from ..format import print_entries, print_json

_DURATION_RE = re.compile(r"^(\d+)([hd])$")


def _parse_since(value: str) -> str:
    """Accept "48h", "2d", or a raw ISO timestamp; return an ISO UTC timestamp."""
    match = _DURATION_RE.match(value.strip())
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        delta = timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
        return (datetime.now(timezone.utc) - delta).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("context", help="recent entries, open threads, tracked refs")
    parser.add_argument("--project", required=True, help="project key")
    parser.add_argument("--since", default="48h", help="lookback window, e.g. 48h, 2d (default 48h)")
    parser.add_argument("--limit", type=int, default=30)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    client = McpClient(args.endpoint or DEFAULT_ENDPOINT)
    try:
        result = client.call_tool(
            "ledger_context",
            {
                "project": args.project,
                "since": _parse_since(args.since),
                "limit": args.limit,
            },
        )
    except (McpTransportError, McpToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print_json(result)
    elif not args.quiet:
        print_entries(result.get("entries", []))
        threads = result.get("open_threads", [])
        if threads:
            print(f"\n{len(threads)} open thread(s):")
            print_entries(threads)
    return 0
