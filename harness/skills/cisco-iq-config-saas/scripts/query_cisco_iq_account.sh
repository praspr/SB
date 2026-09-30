#!/usr/bin/env bash
# Look up Cisco IQ platform accounts by customer name or platform account id.
#
# Calls scripts.cisco.com job API:
#   POST /api/v2/jobs/cisco_iq_account_query
#
# Credentials (never commit these values):
#   BDB_CLIENT_ID
#   BDB_CLIENT_SECRET
# Optional overrides:
#   BDB_TOKEN_URL         (default: https://id.cisco.com/oauth2/default/v1/token)
#   BDB_ACCOUNT_QUERY_URL (default: https://scripts.cisco.com/api/v2/jobs/cisco_iq_account_query)
#
# Resolution order for BDB_CLIENT_ID / BDB_CLIENT_SECRET:
#   existing shell env → $SKILL_DIR/.env → repo .env (if present) → auto-fetch
#   from dev agent-secrets into $SKILL_DIR/.env (created if missing).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TOKEN_URL_DEFAULT="https://id.cisco.com/oauth2/default/v1/token"
API_URL_DEFAULT="https://scripts.cisco.com/api/v2/jobs/cisco_iq_account_query"

BDB_SECRET_ID="cx/usw2/dev01/configbp-ai/secrets/agent-secrets"
BDB_AWS_PROFILE="platform-dev-admin"
BDB_AWS_REGION="us-west-2"

ACCOUNT_SEARCH=""
ACCOUNT_USERS=""
RAW_JSON=0

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name <customer-name-substring>
  bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account <platform-account-id-or-substring>
  bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name hdfc
  bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account 74833d3a-1d15-4060-ad4b-080fea8ce444

Options:
  --name, -n     Search by customer / account name substring (maps to account_search)
  --account, -a  Search by platform account id or substring (maps to account_users)
  --json         Print raw API JSON only (no jq pretty-print)
  -h, --help     Show this help

Environment:
  BDB_CLIENT_ID / BDB_CLIENT_SECRET — auto-loaded from $SKILL_DIR/.env; if
  missing, fetched once from dev agent-secrets and written to that file.
  BDB_TOKEN_URL         optional
  BDB_ACCOUNT_QUERY_URL optional

Exactly one of --name or --account is required.
USAGE
}

load_env_files() {
  local repo_root
  repo_root="$(cd "$SKILL_DIR/../.." 2>/dev/null && pwd || true)"
  if [[ -f "$SKILL_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    source "$SKILL_DIR/.env"
    set +a
  fi
  if [[ -n "$repo_root" && -f "$repo_root/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    source "$repo_root/.env"
    set +a
  fi
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 2
  fi
}

bdb_credentials_present() {
  [[ -n "${BDB_CLIENT_ID:-}" && -n "${BDB_CLIENT_SECRET:-}" ]]
}

fetch_bdb_from_aws() {
  aws secretsmanager get-secret-value \
    --secret-id "$BDB_SECRET_ID" \
    --profile "$BDB_AWS_PROFILE" \
    --region "$BDB_AWS_REGION" \
    --query SecretString --output text \
  | python3 -c '
import json, sys
keys = ["BDB_CLIENT_ID", "BDB_CLIENT_SECRET"]
data = json.load(sys.stdin)
missing = [k for k in keys if not str(data.get(k, "")).strip()]
if missing:
    print("ERROR: agent-secrets missing key(s): " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
for k in keys:
    print(f"{k}={json.dumps(str(data[k]).strip())}")
'
}

merge_bdb_into_skill_env() {
  local incoming_file="$1"
  python3 - <<'PY' "$SKILL_DIR/.env" "$incoming_file"
import sys
from pathlib import Path

skill_env = Path(sys.argv[1])
incoming = Path(sys.argv[2])
updates = {}
for line in incoming.read_text().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        updates[k.strip()] = v.strip().strip('"')

existing = {}
lines = []
if skill_env.exists():
    for raw in skill_env.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            lines.append(raw)
            continue
        if "=" in raw:
            k, v = raw.split("=", 1)
            existing[k.strip()] = v
        else:
            lines.append(raw)

for k, v in updates.items():
    existing[k] = f'"{v}"'

out = []
written = set()
for raw in lines:
    if "=" in raw and not raw.lstrip().startswith("#"):
        k = raw.split("=", 1)[0].strip()
        if k in existing:
            out.append(f"{k}={existing[k]}")
            written.add(k)
        else:
            out.append(raw)
    else:
        out.append(raw)

for k in sorted(existing):
    if k not in written:
        out.append(f"{k}={existing[k]}")

skill_env.parent.mkdir(parents=True, exist_ok=True)
skill_env.write_text("\n".join(out).rstrip() + "\n")
skill_env.chmod(0o600)
PY
}

ensure_bdb_credentials() {
  if bdb_credentials_present; then
    return 0
  fi

  require_cmd aws

  echo "BDB credentials not set; fetching from dev agent-secrets..." >&2

  local tmp_fetch tmp_err
  tmp_fetch="$(mktemp)"
  tmp_err="$(mktemp)"

  if ! fetch_bdb_from_aws >"$tmp_fetch" 2>"$tmp_err"; then
    if grep -qiE 'expired|token|credentials|sso|Unauthorized|AccessDenied' "$tmp_err"; then
      duo-sso
      if ! fetch_bdb_from_aws >"$tmp_fetch" 2>"$tmp_err"; then
        cat "$tmp_err" >&2
        rm -f "$tmp_fetch" "$tmp_err"
        exit 1
      fi
    else
      cat "$tmp_err" >&2
      rm -f "$tmp_fetch" "$tmp_err"
      exit 1
    fi
  fi

  merge_bdb_into_skill_env "$tmp_fetch"
  rm -f "$tmp_fetch" "$tmp_err"
  echo "Updated $SKILL_DIR/.env with BDB_CLIENT_ID / BDB_CLIENT_SECRET." >&2

  # shellcheck disable=SC1091
  set -a
  source "$SKILL_DIR/.env"
  set +a

  if ! bdb_credentials_present; then
    echo "ERROR: failed to load BDB credentials after fetch." >&2
    exit 2
  fi
}

fetch_access_token() {
  local token_url="${BDB_TOKEN_URL:-$TOKEN_URL_DEFAULT}"
  local client_id="${BDB_CLIENT_ID:-}"
  local client_secret="${BDB_CLIENT_SECRET:-}"

  if [[ -z "$client_id" || -z "$client_secret" ]]; then
    cat >&2 <<'EOF'
ERROR: BDB_CLIENT_ID and BDB_CLIENT_SECRET must be set.

The script auto-fetches them from dev agent-secrets into $SKILL_DIR/.env when
missing. If you still see this error, check AWS access (platform-dev-admin +
duo-sso) and that agent-secrets contains both keys.

Do not commit OAuth client secrets to the repository.
EOF
    exit 2
  fi

  local token_response
  token_response="$(
    curl -sS --fail-with-body -X POST "$token_url" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -u "${client_id}:${client_secret}" \
      -d "grant_type=client_credentials"
  )" || {
    echo "ERROR: OAuth token request failed against ${token_url}" >&2
    exit 1
  }

  python3 - <<'PY' "$token_response"
import json, sys
payload = json.loads(sys.argv[1])
token = payload.get("access_token")
if not token:
    print("ERROR: OAuth response missing access_token", file=sys.stderr)
    sys.exit(1)
print(token)
PY
}

build_request_body() {
  python3 - <<'PY' "$ACCOUNT_SEARCH" "$ACCOUNT_USERS"
import json, sys
body = {
    "input": {
        "account_search": sys.argv[1],
        "account_users": sys.argv[2],
    }
}
print(json.dumps(body))
PY
}

call_account_query_api() {
  local access_token="$1"
  local api_url="${BDB_ACCOUNT_QUERY_URL:-$API_URL_DEFAULT}"
  local body
  body="$(build_request_body)"

  curl -sS --fail-with-body -X POST "$api_url" \
    -H "Authorization: Bearer ${access_token}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    --data-binary "$body"
}

print_response() {
  local response="$1"
  if [[ "$RAW_JSON" -eq 1 ]]; then
    printf '%s\n' "$response"
    return
  fi
  if command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$response" | jq .
  else
    python3 - <<'PY' "$response"
import json, sys
print(json.dumps(json.loads(sys.argv[1]), indent=2, sort_keys=True))
PY
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --name|-n)
      ACCOUNT_SEARCH="${2:-}"
      shift 2 || { echo "ERROR: --name requires a value" >&2; exit 2; }
      ;;
    --account|-a)
      ACCOUNT_USERS="${2:-}"
      shift 2 || { echo "ERROR: --account requires a value" >&2; exit 2; }
      ;;
    --json)
      RAW_JSON=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "$ACCOUNT_SEARCH" && -n "$ACCOUNT_USERS" ]]; then
  echo "ERROR: use only one of --name or --account, not both." >&2
  exit 2
fi
if [[ -z "$ACCOUNT_SEARCH" && -z "$ACCOUNT_USERS" ]]; then
  echo "ERROR: provide --name or --account." >&2
  usage >&2
  exit 2
fi

require_cmd curl
require_cmd python3

load_env_files
ensure_bdb_credentials

echo "Fetching OAuth access token..." >&2
ACCESS_TOKEN="$(fetch_access_token)"

echo "Querying Cisco IQ account API..." >&2
RESPONSE="$(call_account_query_api "$ACCESS_TOKEN")"
print_response "$RESPONSE"
