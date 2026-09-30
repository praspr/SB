#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/postgres_query_cache.sh"

KUBE_CONTEXT_DEFAULT_DEV="cx-dev-usw2"
KUBE_NAMESPACE_DEFAULT="sre-baseapps"
POSTGRES_POD_DEFAULT=""
SECRET_NAMESPACE_DEFAULT="cxp-query-service"
SECRET_NAME_DEFAULT="cxp-baqs-creds"
OUTPUT_DIR_DEFAULT="query_outputs"

USER_KUBE_NAMESPACE="${KUBE_NAMESPACE:-}"
USER_POSTGRES_POD="${POSTGRES_POD:-}"
USER_SECRET_NAMESPACE="${SECRET_NAMESPACE:-}"
USER_SECRET_NAME="${SECRET_NAME:-}"
USER_DB_HOST="${DB_HOST:-}"
USER_DB_PORT="${DB_PORT:-}"
USER_DB_NAME="${DB_NAME:-}"
USER_DB_USER="${DB_USER:-}"
USER_DB_PASSWORD="${DB_PASSWORD:-}"

KUBE_NAMESPACE="${KUBE_NAMESPACE:-$KUBE_NAMESPACE_DEFAULT}"
POSTGRES_POD="${POSTGRES_POD:-$POSTGRES_POD_DEFAULT}"
SECRET_NAMESPACE="${SECRET_NAMESPACE:-$SECRET_NAMESPACE_DEFAULT}"
SECRET_NAME="${SECRET_NAME:-$SECRET_NAME_DEFAULT}"
KUBECTL_REQUEST_TIMEOUT="${KUBECTL_REQUEST_TIMEOUT:-15s}"

DB_HOST="${DB_HOST:-}"
DB_PORT="${DB_PORT:-}"
DB_NAME="${DB_NAME:-}"
DB_USER="${DB_USER:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
CACHE_HIT=0
AUTO_DUO_REFRESH_ATTEMPTED=0

nprd_context_for_region() {
  case "$1" in
    usw2) echo "cx-nprd-usw2" ;;
    apse2) echo "cx-nprd-apse2" ;;
    euc1) echo "cx-nprd-euc1" ;;
    *)
      echo "Invalid NPRD region '$1'. Use usw2, apse2, or euc1." >&2
      return 1
      ;;
  esac
}

prod_context_for_region() {
  case "$1" in
    usw2) echo "cx-prd-usw2" ;;
    apse2) echo "cx-prd-apse2" ;;
    euc1) echo "cx-prd-euc1" ;;
    *)
      echo "Invalid PROD region '$1'. Use usw2, apse2, or euc1." >&2
      return 1
      ;;
  esac
}

prompt_region() {
  local env_label="$1"
  local env_display
  env_display="$(printf '%s' "$env_label" | tr '[:lower:]' '[:upper:]')"
  printf '%s\n' "Select ${env_display} region:" "  1) usw2" "  2) apse2" "  3) euc1" >&2
  local choice
  if [[ -r /dev/tty ]]; then
    read -r -p "Enter choice [usw2/apse2/euc1]: " choice < /dev/tty
  else
    read -r -p "Enter choice [usw2/apse2/euc1]: " choice
  fi
  case "$choice" in
    1) echo "usw2" ;;
    2) echo "apse2" ;;
    3) echo "euc1" ;;
    usw2|apse2|euc1) echo "$choice" ;;
    *)
      echo "Invalid ${env_display} region '$choice'. Use usw2, apse2, or euc1." >&2
      return 1
      ;;
  esac
}

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/run_postgres_query.sh"
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" "select * from my_table limit 5;"
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" --excel "select * from my_table limit 5;"

  bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 "select * from my_table limit 5;"
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 "select * from my_table limit 5;"
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 --excel "select * from my_table limit 5;"
  bash "$SKILL_DIR/scripts/run_postgres_query.sh" dev "select 1;"

Behavior:
  - No query provided: opens interactive psql terminal.
  - Query provided: prints results in terminal.
  - Excel output (.xlsx) is OFF by default. Enable per-call with --excel / -x,
    or globally with EXCEL_OUTPUT=1. Use --no-excel to override an env-set default.

Optional env overrides:
  KUBE_CONTEXT, KUBE_NAMESPACE, POSTGRES_POD,
  SECRET_NAMESPACE, SECRET_NAME,
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
  POSTGRES_QUERY_CACHE_DIR, POSTGRES_QUERY_CACHE_CLEAR,
  EXCEL_OUTPUT, OUTPUT_DIR
USAGE
}

perf_trace() {
  if [[ "${POSTGRES_QUERY_PERF_TRACE:-0}" == "1" ]]; then
    printf '[perf] %s %s\n' "$(date +%s.%N)" "$*" >&2
  fi
  return 0
}

parse_cli_env_and_query() {
  CLI_TARGET_ENV=""
  CLI_REGION=""
  CLI_EXCEL_OUTPUT="${EXCEL_OUTPUT:-0}"
  local -a raw
  raw=("$@")
  local -a rest=()
  local i=0
  local seen_env=""

  while [[ $i -lt ${#raw[@]} ]]; do
    local tok="${raw[$i]}"
    if [[ "$tok" == "--excel" || "$tok" == "-x" ]]; then
      CLI_EXCEL_OUTPUT=1
      i=$((i + 1))
      continue
    fi
    if [[ "$tok" == "--no-excel" ]]; then
      CLI_EXCEL_OUTPUT=0
      i=$((i + 1))
      continue
    fi
    if [[ -z "$seen_env" && ( "$tok" == "dev" || "$tok" == "nprd" || "$tok" == "prod" ) ]]; then
      CLI_TARGET_ENV="$tok"
      seen_env=1
      i=$((i + 1))
      continue
    fi
    if [[ ( "$CLI_TARGET_ENV" == "nprd" || "$CLI_TARGET_ENV" == "prod" ) && -z "${CLI_REGION:-}" ]] && \
       [[ "$tok" == "usw2" || "$tok" == "apse2" || "$tok" == "euc1" ]]; then
      CLI_REGION="$tok"
      i=$((i + 1))
      continue
    fi
    rest+=("$tok")
    i=$((i + 1))
  done

  if ((${#rest[@]} > 0)); then
    QUERY_ARGS=("${rest[@]}")
  else
    QUERY_ARGS=()
  fi
}

resolve_kube_context() {
  if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    return
  fi
  case "${CLI_TARGET_ENV:-dev}" in
    dev)
      KUBE_CONTEXT="$KUBE_CONTEXT_DEFAULT_DEV"
      ;;
    nprd)
      local region="${CLI_REGION:-}"
      if [[ -z "$region" ]]; then
        if [[ -t 0 ]]; then
          region="$(prompt_region nprd)" || exit 1
        else
          echo "NPRD requires a region. Example: bash \"\$SKILL_DIR/scripts/run_postgres_query.sh\" nprd usw2 \"select 1;\"" >&2
          exit 1
        fi
      fi
      KUBE_CONTEXT="$(nprd_context_for_region "$region")" || exit 1
      ;;
    prod)
      local region="${CLI_REGION:-}"
      if [[ -z "$region" ]]; then
        if [[ -t 0 ]]; then
          region="$(prompt_region prod)" || exit 1
        else
          echo "PROD requires a region. Example: bash \"\$SKILL_DIR/scripts/run_postgres_query.sh\" prod usw2 \"select 1;\"" >&2
          exit 1
        fi
      fi
      KUBE_CONTEXT="$(prod_context_for_region "$region")" || exit 1
      ;;
    *)
      echo "Invalid target environment '${CLI_TARGET_ENV:-}'. Use dev, nprd, or prod." >&2
      exit 1
      ;;
  esac
}

auth_error_text() {
  printf '%s' "$1" | grep -Eiq 'Unauthorized|must be logged in|provide credentials|ExpiredToken|AccessDenied|could not get token|credential.*expired|exec.*aws.*failed'
}

stale_cached_pod_text() {
  printf '%s' "$1" | grep -Eiq 'not found|NotFound|unable to upgrade connection|container not found|pod .* does not exist'
}

db_auth_error_text() {
  printf '%s' "$1" | grep -Eiq 'password authentication failed|no password supplied'
}

remote_exec_failure_text() {
  printf '%s' "$1" | grep -Eiq 'command terminated with exit code [1-9]|psql: error:'
}

try_auto_duo_sso() {
  if [[ "${AUTO_DUO_SSO:-1}" == "0" ]]; then
    echo "Auto duo-sso disabled (AUTO_DUO_SSO=0). Refresh manually with: duo-sso" >&2
    return 1
  fi
  if (( AUTO_DUO_REFRESH_ATTEMPTED )); then
    echo "Already attempted duo-sso once this run; not retrying." >&2
    return 1
  fi
  if ! command -v duo-sso >/dev/null 2>&1; then
    echo "duo-sso not found on PATH; cannot auto-refresh AWS session." >&2
    return 1
  fi
  AUTO_DUO_REFRESH_ATTEMPTED=1
  echo "AWS session looks expired - running duo-sso to refresh (typically 10-30s)..." >&2
  if duo-sso >&2; then
    echo "duo-sso completed; retrying kubectl..." >&2
    return 0
  fi
  echo "duo-sso failed (exit $?). Refresh manually and re-run." >&2
  return 1
}

kubectl_retry() {
  local err_file out status err_text
  err_file="$(mktemp "${TMPDIR:-/tmp}/postgres_query_kubectl_err_XXXXXX")"
  if out="$(kubectl --request-timeout="$KUBECTL_REQUEST_TIMEOUT" "$@" 2>"$err_file")"; then
    rm -f "$err_file"
    printf '%s' "$out"
    return 0
  fi

  status=$?
  err_text="$(cat "$err_file" 2>/dev/null || true)"
  if auth_error_text "$err_text" && try_auto_duo_sso; then
    if out="$(kubectl --request-timeout="$KUBECTL_REQUEST_TIMEOUT" "$@" 2>"$err_file")"; then
      rm -f "$err_file"
      printf '%s' "$out"
      return 0
    fi
    status=$?
    err_text="$(cat "$err_file" 2>/dev/null || true)"
  fi

  rm -f "$err_file"
  printf '%s\n' "$err_text" >&2
  return "$status"
}

setup_kube_context() {
  local cur_ctx cur_ns
  cur_ctx="$(kubectl config current-context 2>/dev/null || true)"
  cur_ns="$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null || true)"
  if [[ "$cur_ctx" != "$KUBE_CONTEXT" ]]; then
    echo "Setting kubectl context: $KUBE_CONTEXT"
    kubectl config use-context "$KUBE_CONTEXT" >/dev/null
  fi
  if [[ "$cur_ns" != "$KUBE_NAMESPACE" ]]; then
    echo "Setting kubectl namespace: $KUBE_NAMESPACE"
    kubectl config set-context --current --namespace="$KUBE_NAMESPACE" >/dev/null
  fi
}

apply_user_overrides() {
  [[ -n "$USER_KUBE_NAMESPACE" ]] && KUBE_NAMESPACE="$USER_KUBE_NAMESPACE"
  [[ -n "$USER_POSTGRES_POD" ]] && POSTGRES_POD="$USER_POSTGRES_POD"
  [[ -n "$USER_SECRET_NAMESPACE" ]] && SECRET_NAMESPACE="$USER_SECRET_NAMESPACE"
  [[ -n "$USER_SECRET_NAME" ]] && SECRET_NAME="$USER_SECRET_NAME"
  [[ -n "$USER_DB_HOST" ]] && DB_HOST="$USER_DB_HOST"
  [[ -n "$USER_DB_PORT" ]] && DB_PORT="$USER_DB_PORT"
  [[ -n "$USER_DB_NAME" ]] && DB_NAME="$USER_DB_NAME"
  [[ -n "$USER_DB_USER" ]] && DB_USER="$USER_DB_USER"
  [[ -n "$USER_DB_PASSWORD" ]] && DB_PASSWORD="$USER_DB_PASSWORD"
  return 0
}

load_cached_context() {
  if postgres_query_cache_load_context "$KUBE_CONTEXT"; then
    CACHE_HIT=1
    apply_user_overrides
    perf_trace "cache hit for $KUBE_CONTEXT"
    return
  fi
  CACHE_HIT=0
  apply_user_overrides
  perf_trace "cache miss for $KUBE_CONTEXT"
}

ensure_pod_running() {
  local pod="$1"
  local phase
  phase="$(kubectl_retry get pod "$pod" -n "$KUBE_NAMESPACE" -o jsonpath='{.status.phase}' || true)"
  if [[ "$phase" != "Running" ]]; then
    echo "Pod '$pod' in namespace '$KUBE_NAMESPACE' is not Running (phase='${phase:-unknown}')." >&2
    echo "Refusing to exec - would likely hang. Check: kubectl get pod $pod -n $KUBE_NAMESPACE" >&2
    return 1
  fi
}

resolve_postgres_pod() {
  if [[ -n "$POSTGRES_POD" ]]; then
    kubectl_retry get pod "$POSTGRES_POD" -n "$KUBE_NAMESPACE" >/dev/null
    ensure_pod_running "$POSTGRES_POD"
    return
  fi

  local pod_names fallback_pod
  pod_names="$(kubectl_retry get pods -n "$KUBE_NAMESPACE" --field-selector=status.phase=Running -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')"
  fallback_pod="$(printf '%s\n' "$pod_names" | awk '/^sre-debug-tools-pod/{print; exit}')"
  if [[ -z "$fallback_pod" ]]; then
    fallback_pod="$(printf '%s\n' "$pod_names" | awk '/^postgres/{print; exit}')"
  fi
  if [[ -z "$fallback_pod" ]]; then
    echo "Could not find a running sre-debug-tools-pod or postgres pod in namespace '$KUBE_NAMESPACE'." >&2
    return 1
  fi
  POSTGRES_POD="$fallback_pod"
}

parse_secret_json() {
  python3 -c '
import base64
import json
import shlex
import sys

payload = json.load(sys.stdin)
data = payload.get("data", {})
mapping = {
    "SECRET_DB_HOST": "PGHOST",
    "SECRET_DB_PORT": "PGPORT",
    "SECRET_DB_NAME": "PGDATABASE",
    "SECRET_DB_USER": "PGUSER",
    "SECRET_DB_PASSWORD": "dbPassword",
}
for env_name, secret_key in mapping.items():
    encoded = data.get(secret_key, "")
    value = base64.b64decode(encoded).decode("utf-8") if encoded else ""
    print(f"{env_name}={shlex.quote(value)}")
'
}

fetch_connection_values() {
  local secret_json
  secret_json="$(kubectl_retry get secret "$SECRET_NAME" -n "$SECRET_NAMESPACE" -o json)"
  eval "$(printf '%s' "$secret_json" | parse_secret_json)"

  DB_HOST="${DB_HOST:-${SECRET_DB_HOST:-}}"
  DB_PORT="${DB_PORT:-${SECRET_DB_PORT:-}}"
  DB_NAME="${DB_NAME:-${SECRET_DB_NAME:-}}"
  DB_USER="${DB_USER:-${SECRET_DB_USER:-}}"
  DB_PASSWORD="${DB_PASSWORD:-${SECRET_DB_PASSWORD:-}}"
}

ensure_connection_values() {
  if [[ -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASSWORD" ]]; then
    fetch_connection_values
  fi

  if [[ -z "$DB_PASSWORD" ]]; then
    if [[ -r /dev/tty ]]; then
      read -rsp "Postgres password: " DB_PASSWORD < /dev/tty
      echo
    else
      echo "DB password not available from secret '${SECRET_NAMESPACE}/${SECRET_NAME}' and no TTY to prompt." >&2
      echo "Set DB_PASSWORD env var, or run interactively." >&2
      exit 1
    fi
  fi

  local required
  for required in DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD; do
    if [[ -z "${!required:-}" ]]; then
      echo "Missing required connection value: $required" >&2
      echo "Provide via env var, or ensure secret ${SECRET_NAMESPACE}/${SECRET_NAME} has required keys." >&2
      exit 1
    fi
  done
}

refresh_cached_values() {
  perf_trace "refreshing cluster values for $KUBE_CONTEXT"
  postgres_query_cache_clear_context "$KUBE_CONTEXT"
  CACHE_HIT=0

  POSTGRES_POD="${USER_POSTGRES_POD:-$POSTGRES_POD_DEFAULT}"
  DB_HOST="$USER_DB_HOST"
  DB_PORT="$USER_DB_PORT"
  DB_NAME="$USER_DB_NAME"
  DB_USER="$USER_DB_USER"
  DB_PASSWORD="$USER_DB_PASSWORD"
  apply_user_overrides

  resolve_postgres_pod
  ensure_connection_values
  postgres_query_cache_write_context "$KUBE_CONTEXT"
}

refresh_secret_values() {
  if [[ -n "$USER_DB_PASSWORD" ]]; then
    return 1
  fi

  echo "Cached DB credentials appear stale; refreshing secret values and retrying..." >&2
  DB_HOST="$USER_DB_HOST"
  DB_PORT="$USER_DB_PORT"
  DB_NAME="$USER_DB_NAME"
  DB_USER="$USER_DB_USER"
  DB_PASSWORD="$USER_DB_PASSWORD"
  apply_user_overrides
  fetch_connection_values
  ensure_connection_values
  postgres_query_cache_write_context "$KUBE_CONTEXT"
}

prepare_connection() {
  load_cached_context
  if [[ "$CACHE_HIT" != "1" || -z "$POSTGRES_POD" || -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASSWORD" ]]; then
    resolve_postgres_pod
    ensure_connection_values
    postgres_query_cache_write_context "$KUBE_CONTEXT"
  fi
}

LAST_EXEC_ERR_TEXT=""
run_preserving_stderr() {
  local err_file="$1"
  shift
  local fifo status tee_pid

  : > "$err_file"
  fifo="${err_file}.fifo"
  rm -f "$fifo"
  mkfifo "$fifo"
  tee "$err_file" < "$fifo" >&2 &
  tee_pid=$!

  set +e
  "$@" 2> "$fifo"
  status=$?
  set -e

  wait "$tee_pid" 2>/dev/null || true
  rm -f "$fifo"

  LAST_EXEC_ERR_TEXT="$(cat "$err_file" 2>/dev/null || true)"
  if [[ "$status" -eq 0 ]] && remote_exec_failure_text "$LAST_EXEC_ERR_TEXT"; then
    return 1
  fi
  return "$status"
}

run_psql_query_table_once() {
  local sql="$1"
  {
    printf '%s\n' '\timing on'
    printf '%s\n' "$sql"
  } | kubectl exec -i "$POSTGRES_POD" -n "$KUBE_NAMESPACE" -- \
    env PGPASSWORD="$DB_PASSWORD" \
    psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -v ON_ERROR_STOP=1 \
      -P pager=off
}

run_psql_query_csv_once() {
  local sql="$1"
  local out_file="$2"
  {
    printf '%s\n' "$sql"
  } | kubectl exec -i "$POSTGRES_POD" -n "$KUBE_NAMESPACE" -- \
    env PGPASSWORD="$DB_PASSWORD" \
    psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -v ON_ERROR_STOP=1 \
      -P pager=off \
      --csv > "$out_file"
}

run_with_exec_retry() {
  local label="$1"
  shift
  local err_file status err_text attempts auth_attempted stale_attempted secret_attempted
  err_file="$(mktemp "${TMPDIR:-/tmp}/postgres_query_exec_err_XXXXXX")"

  attempts=0
  auth_attempted=0
  stale_attempted=0
  secret_attempted=0

  while (( attempts < 4 )); do
    if run_preserving_stderr "$err_file" "$@"; then
      rm -f "$err_file"
      return 0
    else
      status=$?
    fi

    err_text="$LAST_EXEC_ERR_TEXT"

    if [[ "$auth_attempted" == "0" ]] && auth_error_text "$err_text" && try_auto_duo_sso; then
      auth_attempted=1
      attempts=$((attempts + 1))
      continue
    fi

    if [[ "$stale_attempted" == "0" ]] && stale_cached_pod_text "$err_text"; then
      echo "Cached pod or connection data appears stale; refreshing cache and retrying $label..." >&2
      if refresh_cached_values; then
        stale_attempted=1
        attempts=$((attempts + 1))
        continue
      fi
    fi

    if [[ "$secret_attempted" == "0" ]] && db_auth_error_text "$err_text" && refresh_secret_values; then
      secret_attempted=1
      attempts=$((attempts + 1))
      continue
    fi

    break
  done

  rm -f "$err_file"
  return "$status"
}

csv_to_excel() {
  local csv_file="$1"
  local xlsx_file="$2"

  python3 - "$csv_file" "$xlsx_file" <<'PY'
import csv
import sys

try:
    from openpyxl import Workbook
except Exception:
    raise SystemExit("openpyxl is required to write Excel output. Install with: uv pip install openpyxl")

csv_path = sys.argv[1]
xlsx_path = sys.argv[2]

wb = Workbook()
ws = wb.active
ws.title = "query_results"

with open(csv_path, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        ws.append(row)

wb.save(xlsx_path)
PY
}

main() {
  local query=""

  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  parse_cli_env_and_query "$@"

  if [[ ${#QUERY_ARGS[@]} -gt 0 ]]; then
    query="${QUERY_ARGS[*]}"
  elif [[ -p /dev/stdin || ( ! -t 0 && -f /dev/stdin ) ]]; then
    echo "Reading query from stdin..." >&2
    query="$(cat)"
  fi

  resolve_kube_context
  setup_kube_context
  prepare_connection

  echo "Context: $KUBE_CONTEXT"
  echo "Namespace: $KUBE_NAMESPACE"
  echo "Pod: $POSTGRES_POD"
  echo "Target DB: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

  if [[ -z "${query//[[:space:]]/}" ]]; then
    if [[ ! -t 0 || ! -t 1 ]]; then
      echo "No query provided and no interactive terminal detected." >&2
      exit 1
    fi

    trap 'unset DB_PASSWORD PGPASSWORD' EXIT
    echo "Opening interactive psql session (use \\q to exit)..."
    run_with_exec_retry "interactive psql" kubectl exec -it "$POSTGRES_POD" -n "$KUBE_NAMESPACE" -- \
      env PGPASSWORD="$DB_PASSWORD" \
      psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME"
    return $?
  fi

  if [[ "${CLI_EXCEL_OUTPUT:-0}" != "1" ]]; then
    trap 'unset DB_PASSWORD PGPASSWORD' EXIT
    echo "Executing query and printing results..."
    run_with_exec_retry "query" run_psql_query_table_once "$query"
    return $?
  fi

  local output_dir="${OUTPUT_DIR:-$OUTPUT_DIR_DEFAULT}"
  local timestamp unique csv_tmp excel_file

  timestamp="$(date +%Y%m%d_%H%M%S)"
  unique="$$_$(printf '%04x' $((RANDOM * RANDOM & 0xffff)))"
  mkdir -p "$output_dir"
  csv_tmp="$(mktemp "${TMPDIR:-/tmp}/query_result_${timestamp}_${unique}_XXXXXX.csv")"
  excel_file="$output_dir/query_${timestamp}_${unique}.xlsx"

  trap 'rm -f "${csv_tmp:-}"; unset DB_PASSWORD PGPASSWORD' EXIT

  echo "Executing query and printing results..."
  run_with_exec_retry "query" run_psql_query_table_once "$query" || return $?

  echo "Creating Excel output..."
  run_with_exec_retry "csv export" run_psql_query_csv_once "$query" "$csv_tmp" || return $?
  csv_to_excel "$csv_tmp" "$excel_file"

  echo "Saved Excel file: $excel_file"
}

main "$@"
