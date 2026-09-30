"""`sb projects` — list and enroll ledger projects."""

from __future__ import annotations

import argparse
import sys

from ..client import DEFAULT_ENDPOINT, McpClient, McpToolError, McpTransportError
from ..format import print_json, print_projects


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("projects", help="list or enroll ledger projects")
    project_sub = parser.add_subparsers(dest="projects_command", required=True)

    list_parser = project_sub.add_parser("list", help="list enrolled projects")
    list_parser.set_defaults(func=run_list)

    enroll_parser = project_sub.add_parser("enroll", help="enroll a project")
    enroll_parser.add_argument("--project", required=True, dest="project_name")
    enroll_parser.add_argument("--path", required=True, dest="root_path")
    enroll_parser.add_argument("--changelog", default=None, dest="changelog_path")
    enroll_parser.add_argument(
        "--sync-mode", default="dual", choices=["dual", "sqlite-only"], dest="sync_mode"
    )
    enroll_parser.set_defaults(func=run_enroll)


def run_list(args: argparse.Namespace) -> int:
    client = McpClient(args.endpoint or DEFAULT_ENDPOINT)
    try:
        result = client.call_tool("ledger_projects")
    except (McpTransportError, McpToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print_json(result)
    else:
        print_projects(result, quiet=args.quiet)
    return 0


def run_enroll(args: argparse.Namespace) -> int:
    client = McpClient(args.endpoint or DEFAULT_ENDPOINT)
    try:
        result = client.call_tool(
            "ledger_register_project",
            {
                "project": args.project_name,
                "root_path": args.root_path,
                "changelog_path": args.changelog_path,
                "sync_mode": args.sync_mode,
            },
        )
    except (McpTransportError, McpToolError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print_json(result)
    elif not args.quiet:
        print(f"enrolled {result['project']} -> {result['changelog_path']} ({result['sync_mode']})")
    return 0
