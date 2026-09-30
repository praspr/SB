#!/usr/bin/env bash
# run_splunk_trace_query.sh
#
# Fetch a SignalFx APM trace via the GraphQL endpoint documented in
# docs/splunk-observability.md (the public REST trace-download API 404s for
# this org; introspection is disabled on the GraphQL schema too).
#
# Realm is hardcoded to us1 (confirmed for Cisco Systems Inc. — see the doc).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GRAPHQL_URL="https://api.us1.signalfx.com/v2/apm/graphql"

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" <trace-id> [--tags] [--sql] [--json]

Options:
  --tags   Include the full tags[] array (key/value) per span.
  --sql    Print only spans carrying a db.statement tag (operationName,
           duration, and the literal/parameterized SQL) — implies --tags.
  --json   Print the raw GraphQL response instead of the formatted waterfall.
  -h, --help

Examples:
  bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" 4bf92f3577b34da6a3ce929d0e0e4736
  bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" 4bf92f3577b34da6a3ce929d0e0e4736 --sql

Token resolution order: $SPLUNK_API_TOKEN env var, then SPLUNK_API_TOKEN in
this skill's .env, then an interactive prompt (TTY required) that saves the
entered token to ~/.zshrc or ~/.bashrc (whichever matches $SHELL, applies to
new shells) and exports it for this run. Never search the repo/secrets
stores for a substitute.

To get a token: https://cisco-cx-observe.signalfx.com -> top-right profile
menu -> My Profile -> "Show User API Access Token" (top right of that page)
-> copy it.

Gotcha (see docs/splunk-observability.md): this query silently truncates on
very large traces (deeply nested connector-level spans go missing). For
large configbp-ai traces, fall back to the Splunk UI directly.
USAGE
}

TRACE_ID=""
WANT_TAGS=0
WANT_SQL=0
WANT_JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --tags) WANT_TAGS=1; shift ;;
    --sql) WANT_SQL=1; WANT_TAGS=1; shift ;;
    --json) WANT_JSON=1; shift ;;
    -*) echo "ERROR: unknown flag: $1" >&2; exit 2 ;;
    *)
      if [[ -n "$TRACE_ID" ]]; then
        echo "ERROR: unexpected extra argument: $1" >&2
        exit 2
      fi
      TRACE_ID="$1"
      shift
      ;;
  esac
done

if [[ -z "$TRACE_ID" ]]; then
  echo "ERROR: missing <trace-id>." >&2
  usage >&2
  exit 2
fi

rc_file_for_shell() {
  case "$(basename "${SHELL:-/bin/bash}")" in
    zsh) echo "$HOME/.zshrc" ;;
    bash) echo "$HOME/.bashrc" ;;
    *) echo "$HOME/.zshrc" ;;
  esac
}

prompt_and_persist_token() {
  local rc_file token
  if ! { exec 3</dev/tty; } 2>/dev/null; then
    echo "ERROR: SPLUNK_API_TOKEN not found in env or $SKILL_DIR/.env, and no TTY to prompt." >&2
    echo "Ask the user to provide it — do not search elsewhere for a substitute." >&2
    exit 1
  fi

  echo "SPLUNK_API_TOKEN not set. To get one: https://cisco-cx-observe.signalfx.com -> top-right profile menu -> My Profile -> \"Show User API Access Token\" button (top right of that page) -> copy it." >&2
  read -rsp "Enter SPLUNK_API_TOKEN: " token <&3
  exec 3<&-
  echo >&2
  if [[ -z "$token" ]]; then
    echo "ERROR: no token entered." >&2
    exit 1
  fi

  rc_file="$(rc_file_for_shell)"
  if [[ -f "$rc_file" ]] && grep -q "^export SPLUNK_API_TOKEN=" "$rc_file"; then
    # shellcheck disable=SC1003
    sed -i '' "s|^export SPLUNK_API_TOKEN=.*|export SPLUNK_API_TOKEN='${token}'|" "$rc_file"
  else
    { printf '\n# Added by run_splunk_trace_query.sh\n'; printf "export SPLUNK_API_TOKEN='%s'\n" "$token"; } >> "$rc_file"
  fi
  echo "Saved SPLUNK_API_TOKEN to $rc_file (will apply to new shells)." >&2

  # Not sourcing $rc_file here: it's a real shell's rc file (may contain
  # zsh-only syntax, e.g. compinit/bun completions) which breaks when
  # sourced from this bash script regardless of the user's login shell.
  # The token is already known in-process, so just export it directly.
  SPLUNK_API_TOKEN="$token"
}

SPLUNK_API_TOKEN="${SPLUNK_API_TOKEN:-}"
if [[ -z "$SPLUNK_API_TOKEN" && -f "$SKILL_DIR/.env" ]]; then
  SPLUNK_API_TOKEN="$(grep "^SPLUNK_API_TOKEN=" "$SKILL_DIR/.env" | head -1 | cut -d'=' -f2- | tr -d '"'"'"'')"
fi
if [[ -z "$SPLUNK_API_TOKEN" ]]; then
  prompt_and_persist_token
fi

SPAN_FIELDS="spanID operationName serviceName duration startTime"
if (( WANT_TAGS )); then
  SPAN_FIELDS="$SPAN_FIELDS tags { key value }"
fi

QUERY="query { trace(id: \"${TRACE_ID}\") { traceID spans { ${SPAN_FIELDS} } } }"
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"query": sys.argv[1]}))' "$QUERY")"

RESPONSE="$(curl -sS -X POST "$GRAPHQL_URL" \
  -H "X-SF-Token: $SPLUNK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")"

if (( WANT_JSON )); then
  printf '%s\n' "$RESPONSE"
  exit 0
fi

WANT_SQL="$WANT_SQL" python3 -c '
import json
import os
import sys

resp = json.loads(sys.argv[1])
if "errors" in resp:
    print(json.dumps(resp["errors"], indent=2), file=sys.stderr)
    sys.exit(1)

trace = (resp.get("data") or {}).get("trace")
if not trace:
    print("No trace data returned (bad trace ID, or trace not found).", file=sys.stderr)
    sys.exit(1)

spans = sorted(trace["spans"], key=lambda s: s.get("startTime") or 0)
want_sql = os.environ.get("WANT_SQL") == "1"

for s in spans:
    tags = {t["key"]: t["value"] for t in s.get("tags") or []}
    sql = tags.get("db.statement") or tags.get("db.query.text")
    if want_sql:
        if sql:
            op = s["operationName"]
            dur = s["duration"]
            svc = s["serviceName"]
            print(f"{op}  {dur}us  [{svc}]")
            print(f"  {sql}")
    else:
        start = s["startTime"]
        dur = s["duration"]
        svc = s["serviceName"]
        op = s["operationName"]
        print(f"{start:>18}  {dur:>10}us  {svc:<28} {op}")
' "$RESPONSE"
