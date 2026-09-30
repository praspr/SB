"""Entry point for the ``sb`` CLI: ``sb log|context|search|projects``."""

from __future__ import annotations

import argparse
import sys

from .client import DEFAULT_ENDPOINT
from .commands import context as context_cmd
from .commands import log as log_cmd
from .commands import projects as projects_cmd
from .commands import search as search_cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sb", description="Command-line client for the sb narrative ledger."
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"sb-core MCP endpoint (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument("--json", action="store_true", help="print raw JSON output")
    parser.add_argument("--quiet", action="store_true", help="suppress non-error output")

    subparsers = parser.add_subparsers(dest="command", required=True)
    log_cmd.add_parser(subparsers)
    context_cmd.add_parser(subparsers)
    search_cmd.add_parser(subparsers)
    projects_cmd.add_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
