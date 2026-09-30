"""`sb search` — full-text and filtered ledger search."""

from __future__ import annotations

import argparse
import sys

from ..client import DEFAULT_ENDPOINT, McpClient, McpToolError, McpTransportError
from ..format import print_entries, print_json
from .context import _parse_since


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("search", help="search the ledger")
    parser.add_argument("query", nargs="?", default=None, help="full-text query")
    parser.add_argument("--project", default=None)
    parser.add_argument("--since", default=None, help="e.g. 48h, 2d, or an ISO timestamp")
    parser.add_argument("--verb", default=None, dest="action_verb")
    parser.add_argument("--limit", type=int, default=50)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    client = McpClient(args.endpoint or DEFAULT_ENDPOINT)
    since = _parse_since(args.since) if args.since else None
    try:
        result = client.call_tool(
            "ledger_search",
            {
                "q": args.query,
                "project": args.project,
                "since": since,
                "verb": args.action_verb,
                "limit": args.limit,
            },
        )
    except (McpTransportError, McpToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print_json(result)
    else:
        print_entries(result, quiet=args.quiet)
    return 0
