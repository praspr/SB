"""`sb log` — record one ledger entry."""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional

from ..client import DEFAULT_ENDPOINT, McpClient, McpToolError, McpTransportError
from ..format import print_json, print_log_result


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("log", help="record one ledger entry")
    parser.add_argument("summary", help="one-line narrative summary")
    parser.add_argument("--project", required=True, help="project key, e.g. sb or ciq")
    parser.add_argument("--scope", default=None, help="scope label, e.g. a repo/module name")
    parser.add_argument("--verb", default="Note", dest="action_verb", help="past-tense action verb")
    parser.add_argument(
        "--ref",
        action="append",
        default=[],
        metavar="KIND=VALUE[:URL]",
        help="attach a reference; repeatable, e.g. --ref pr=45:https://github.com/org/repo/pull/45",
    )
    parser.add_argument("--session", default=None, dest="session_id", help="explicit session id")
    parser.add_argument("--body", default=None, help="optional longer narrative body")
    parser.set_defaults(func=run)


_URL_SPLIT_RE = re.compile(r":(?=[A-Za-z][A-Za-z0-9+.-]*://)")


def _parse_ref(raw: str) -> dict:
    if "=" not in raw:
        raise ValueError(f"invalid --ref {raw!r}: expected KIND=VALUE[:URL]")
    kind, rest = raw.split("=", 1)
    parts = _URL_SPLIT_RE.split(rest, maxsplit=1)
    if len(parts) == 2:
        value, url = parts
    else:
        value, url = rest, None
    ref: dict = {"kind": kind, "value": value}
    if url:
        ref["url"] = url
    return ref


def run(args: argparse.Namespace) -> int:
    try:
        refs = [_parse_ref(r) for r in args.ref]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    client = McpClient(args.endpoint or DEFAULT_ENDPOINT)
    agent = os.environ.get("SB_AGENT", "cli")
    working_dir = os.getcwd()

    try:
        result = client.call_tool(
            "ledger_log",
            {
                "summary": args.summary,
                "project": args.project,
                "action_verb": args.action_verb,
                "body": args.body,
                "scope": args.scope,
                "refs": refs or None,
                "session_id": args.session_id,
                "agent": agent,
                "working_dir": working_dir,
                "source_harness": "sb-log-cli",
            },
        )
    except (McpTransportError, McpToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print_json(result)
    else:
        print_log_result(result, quiet=args.quiet)
    return 0
