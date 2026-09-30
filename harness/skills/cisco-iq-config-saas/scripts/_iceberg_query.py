"""Athena/Glue query executor used by run_iceberg_query.sh.

Queries UDM Iceberg tables directly via Amazon Athena against the Glue
Data Catalog, bypassing Trino/APISIX entirely. Auth is a plain AWS SSO
profile (platform-<env>-admin) refreshed by duo-sso — no
TRINO_SERVICE_CREDENTIALS, no local port-forward, no sudo.

Not meant to be run directly — invoke run_iceberg_query.sh instead.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

_REQUIRED_DEPS: dict[str, str] = {
    "boto3": "boto3",
    "tabulate": "tabulate",
    "openpyxl": "openpyxl",
}


def _check_required_deps() -> None:
    missing_imports: list[str] = []
    missing_pip_names: list[str] = []
    for import_name, pip_name in _REQUIRED_DEPS.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_imports.append(import_name)
            missing_pip_names.append(pip_name)
    if missing_imports:
        sys.stderr.write(
            "ERROR: missing required Python package(s): "
            + ", ".join(missing_imports)
            + "\n\nInstall them all with:\n\n  uv pip install "
            + " ".join(missing_pip_names)
            + "\n\n(If you use a virtualenv, activate it first.)\n"
        )
        raise SystemExit(2)


def _require(pkg: str):
    try:
        return __import__(pkg)
    except ImportError as exc:  # noqa: BLE001
        pip_name = _REQUIRED_DEPS.get(pkg, pkg)
        sys.stderr.write(
            f"ERROR: missing required Python package: {pkg}\nInstall with:  pip3 install {pip_name}\n"
        )
        raise SystemExit(2) from exc


# ---------- output coercion (shared shape with _iceberg_query.py) -------


def _coerce_cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_coerce_cell(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _coerce_cell(x) for k, x in v.items()}
    return str(v)


def _truncate(s: str, n: int) -> str:
    if n <= 0 or len(s) <= n:
        return s
    return s[: n - 1] + "…"


# ---------- auth: auto duo-sso retry on expired/missing SSO creds -------
#
# Athena auth is a plain AWS SSO profile (platform-<env>-admin), already
# refreshed by the user's normal `duo-sso` flow and cached by the AWS CLI
# under ~/.aws/sso/cache. There is no secret to fetch and no principal to
# harvest (unlike the Trino/APISIX path), so the only failure mode worth
# auto-recovering from is an expired/missing SSO token — one retry via
# duo-sso, mirroring run_postgres_query.sh's try_auto_duo_sso.

_AUTO_DUO_REFRESH_ATTEMPTED = False


def _is_sso_auth_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name in {
        "UnauthorizedSSOTokenError",
        "TokenRetrievalError",
        "SSOTokenLoadError",
        "ExpiredTokenException",
        "UnrecognizedClientException",
        "NoCredentialsError",
    }:
        return True
    msg = str(exc)
    return any(
        s in msg
        for s in (
            "ExpiredToken",
            "token has expired",
            "Error loading SSO Token",
            "is not authorized to perform",
            "AccessDenied",
        )
    )


def _try_auto_duo_sso() -> bool:
    global _AUTO_DUO_REFRESH_ATTEMPTED
    if os.environ.get("AUTO_DUO_SSO", "1") == "0":
        print(
            "Auto duo-sso disabled (AUTO_DUO_SSO=0). Refresh manually with: duo-sso",
            file=sys.stderr,
        )
        return False
    if _AUTO_DUO_REFRESH_ATTEMPTED:
        print("Already attempted duo-sso once this run; not retrying.", file=sys.stderr)
        return False
    _AUTO_DUO_REFRESH_ATTEMPTED = True
    print(
        "AWS session looks expired - running duo-sso to refresh (typically 10-30s)...",
        file=sys.stderr,
    )
    try:
        result = subprocess.run(["duo-sso"], timeout=60)
    except FileNotFoundError:
        print(
            "duo-sso not found on PATH; cannot auto-refresh AWS session.",
            file=sys.stderr,
        )
        return False
    except subprocess.TimeoutExpired:
        print("duo-sso timed out.", file=sys.stderr)
        return False
    if result.returncode == 0:
        print("duo-sso completed; retrying...", file=sys.stderr)
        return True
    print(
        f"duo-sso failed (exit {result.returncode}). Refresh manually and re-run.",
        file=sys.stderr,
    )
    return False


def _with_auth_retry(fn):
    """Call fn() once; on an SSO auth error, run duo-sso and retry once."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        if _is_sso_auth_error(exc) and _try_auto_duo_sso():
            return fn()
        raise


# ---------- Athena client + query execution -----------------------------


@dataclass(slots=True)
class AthenaConn:
    profile: str
    region: str
    database: str
    workgroup: str
    output_s3: str | None = None
    poll_interval: float = 1.0

    def client(self):
        boto3 = _require("boto3")
        session = boto3.Session(profile_name=self.profile, region_name=self.region)
        return session.client("athena")


def _run_query(
    conn: AthenaConn, sql: str, timeout: int
) -> tuple[Sequence[str], Sequence[Sequence[Any]]]:
    athena = conn.client()

    def start():
        kwargs: dict[str, Any] = {
            "QueryString": sql,
            "QueryExecutionContext": {"Database": conn.database},
            "WorkGroup": conn.workgroup,
        }
        # OutputLocation is only needed if the workgroup has no default
        # result configuration. Omit it so Athena falls back to whatever
        # the workgroup already has configured server-side — avoids
        # hardcoding a per-env/region S3 bucket that may not exist.
        if conn.output_s3:
            kwargs["ResultConfiguration"] = {"OutputLocation": conn.output_s3}
        return athena.start_query_execution(**kwargs)["QueryExecutionId"]

    qid = _with_auth_retry(start)

    deadline = time.time() + timeout
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"][
            "Status"
        ]
        state = status["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            reason = status.get("StateChangeReason") or status.get(
                "AthenaError", {}
            ).get("Message")
            raise RuntimeError(f"Athena query {state}: {reason}")
        if time.time() >= deadline:
            raise TimeoutError(f"Athena query timed out after {timeout}s (id={qid})")
        time.sleep(conn.poll_interval)

    cols: list[str] = []
    rows: list[list[Any]] = []
    next_token: str | None = None
    first_page = True
    while True:
        kwargs: dict[str, Any] = {"QueryExecutionId": qid, "MaxResults": 1000}
        if next_token:
            kwargs["NextToken"] = next_token
        page = athena.get_query_results(**kwargs)
        result_rows = page["ResultSet"]["Rows"]

        if first_page:
            col_info = page["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
            cols = [c["Name"] for c in col_info]
            # Athena's first result row repeats the header for non-DDL
            # SELECTs; DDL/SHOW statements don't. Detect and skip it.
            if (
                result_rows
                and [d.get("VarCharValue") for d in result_rows[0]["Data"]] == cols
            ):
                result_rows = result_rows[1:]
            first_page = False

        for row in result_rows:
            rows.append([d.get("VarCharValue") for d in row["Data"]])

        next_token = page.get("NextToken")
        if not next_token:
            break

    return cols, rows


# ---------- output formatters (identical shape to _iceberg_query.py) ----


def _print_table(
    cols: Sequence[str], rows: Sequence[Sequence[Any]], *, truncate_at: int
) -> None:
    coerced: list[list[str]] = []
    for r in rows:
        coerced.append(
            ["NULL" if v is None else _truncate(str(v), truncate_at) for v in r]
        )
    try:
        from tabulate import tabulate

        print(tabulate(coerced, headers=list(cols), tablefmt="psql"))
    except ImportError:
        widths = [len(c) for c in cols]
        for r in coerced:
            for i, cell in enumerate(r):
                if len(cell) > widths[i]:
                    widths[i] = len(cell)
        sep = "+".join("-" * (w + 2) for w in widths)
        print("+" + sep + "+")
        print("| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |")
        print("+" + sep + "+")
        for r in coerced:
            print("| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(r)) + " |")
        print("+" + sep + "+")


def _emit_json(cols: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    out = [{c: _coerce_cell(v) for c, v in zip(cols, r)} for r in rows]
    json.dump(out, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _write_csv(path: Path, cols: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])


def _write_xlsx(path: Path, cols: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    openpyxl = _require("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "athena_results"
    ws.append(list(cols))
    for r in rows:
        ws.append([None if v is None else v for v in r])
    wb.save(path)


def _emit_results(
    args: argparse.Namespace, cols: Sequence[str], rows: Sequence[Sequence[Any]]
) -> None:
    if args.json:
        _emit_json(cols, rows)
    else:
        _print_table(cols, rows, truncate_at=args.truncate)

    if args.csv_path:
        path = Path(args.csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(path, cols, rows)
        print(f"\nSaved CSV: {path}", file=sys.stderr)

    if args.xlsx_path:
        path = Path(args.xlsx_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_xlsx(path, cols, rows)
        print(f"Saved Excel: {path}", file=sys.stderr)


def _run_repl(args: argparse.Namespace, conn: AthenaConn) -> int:
    print(
        f"Athena REPL  database={conn.database}  workgroup={conn.workgroup}",
        file=sys.stderr,
    )
    print(
        "Enter SQL terminated by a semicolon on its own line, or just a blank line.\n"
        "Commands:  \\q quit",
        file=sys.stderr,
    )
    buf: list[str] = []
    while True:
        try:
            line = input("athena> " if not buf else "     -> ")
        except EOFError:
            print()
            break
        stripped = line.strip()
        if not buf and stripped in {"\\q", "\\quit", "exit", "quit"}:
            break
        buf.append(line)
        joined = "\n".join(buf).strip()
        if joined.endswith(";") or (stripped == "" and joined):
            sql = joined.rstrip(";").strip()
            buf.clear()
            if not sql:
                continue
            try:
                cols, rows = _run_query(conn, sql, args.timeout)
                _print_table(cols, rows, truncate_at=args.truncate)
                print(f"({len(rows)} rows)\n", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                print(f"Athena error: {exc}\n", file=sys.stderr)
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="_iceberg_query.py",
        description=(
            "Internal helper for run_iceberg_query.sh — executes one SQL "
            "statement (or runs an interactive REPL) against Athena/Glue "
            "for UDM Iceberg tables."
        ),
    )
    p.add_argument("--sql", default=None, help="SQL to execute. Omit for REPL mode.")
    p.add_argument(
        "--repl", action="store_true", help="Force REPL mode even if --sql given."
    )
    p.add_argument(
        "--json", action="store_true", help="Emit results as JSON to stdout."
    )
    p.add_argument("--csv-path", default=None, help="Also write CSV to this path.")
    p.add_argument("--xlsx-path", default=None, help="Also write XLSX to this path.")
    p.add_argument(
        "--truncate",
        type=int,
        default=int(os.environ.get("ICEBERG_QUERY_TRUNCATE", "120")),
        help="Truncate cell display to N chars (table mode only). 0 = no truncation.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("ICEBERG_QUERY_TIMEOUT", "120")),
        help="Query timeout in seconds.",
    )
    return p


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    _check_required_deps()

    profile = os.environ["ICEBERG_PROFILE"]
    region = os.environ["ICEBERG_REGION"]
    database = os.environ["ICEBERG_DATABASE"]
    output_s3 = os.environ.get("ICEBERG_OUTPUT_S3") or None
    workgroup = os.environ.get("ICEBERG_WORKGROUP", "primary")

    conn = AthenaConn(
        profile=profile,
        region=region,
        database=database,
        output_s3=output_s3,
        workgroup=workgroup,
    )

    if args.repl or not args.sql:
        return _run_repl(args, conn)

    sql = args.sql.strip()
    if not sql:
        sys.stderr.write("ERROR: empty SQL string.\n")
        return 2

    try:
        cols, rows = _with_auth_retry(lambda: _run_query(conn, sql, args.timeout))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Athena error: {exc}\n")
        return 1

    _emit_results(args, cols, rows)
    print(f"\n({len(rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
