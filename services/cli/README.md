# sb-cli

Command-line client for the sb narrative ledger. Talks to `sb-core`'s
unified MCP endpoint (`http://127.0.0.1:8787/mcp` by default) — no separate
server of its own.

## Install

```bash
cd sb/services/cli
uv sync --group dev
```

## Usage

```bash
sb log "Shipped the ledger foundation" --project sb --verb Shipped
sb log "Fixed the auth bug" --project sb --scope core --ref pr=45:https://github.com/org/repo/pull/45
sb context --project sb --since 48h
sb search "APISIX" --project sb --since 2d
sb projects list
sb projects enroll --project demo --path /abs/path --sync-mode dual
```

Common flags: `--endpoint` (default `http://127.0.0.1:8787/mcp`), `--json`
(raw JSON output), `--quiet` (suppress non-error output).

`sb log` auto-derives `agent` from `$SB_AGENT` (default `"cli"`), the
working directory from `os.getcwd()`, and tags the entry
`source_harness="sb-log-cli"`.

Exit codes: nonzero only on transport failures (sb-core unreachable, HTTP
error). A content-level "already recorded" idempotent no-op exits `0` with a
friendly note.

## Tests

```bash
cd sb/services/cli
uv run pytest -q
```
