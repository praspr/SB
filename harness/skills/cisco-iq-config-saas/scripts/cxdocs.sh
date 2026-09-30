#!/usr/bin/env bash
# cxdocs.sh
#
# cxdocs.cisco.com (CX Platform Docs / Cisco IQ documentation / IQ docs /
# cxdocs) access via the internal `cxdocs-cli` tool
# (github.com/CXEPI/cxdocs-cli). See docs/cxdocs-cli.md.
#
# Subcommands:
#   fetch <url> [--full|--body|--nav]   Fetch a known page as markdown.
#   search <query> [--limit N] [--refresh]
#                                        Find the right page URL by keyword.
#
# Auto-installs cxdocs-cli via `uv tool install` if it is not on PATH.
# Does NOT run `cxdocs-cli login` — that is an interactive browser/Duo SSO
# flow the user must run themselves in their own terminal (see
# docs/cxdocs-cli.md and the "cxdocs-cli agent behavior" section of
# SKILL.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CXDOCS_ORG="CXEPI"
CXDOCS_REPO_PATH="cxdocs-cli.git"
CXDOCS_BASE_URL="https://cxdocs.cisco.com"
CACHE_DIR="$SKILL_DIR/.cache/cxdocs"
CACHE_FILE="$CACHE_DIR/search_index.json"

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/cxdocs.sh" fetch <url> [--full|--body|--nav]
  bash "$SKILL_DIR/scripts/cxdocs.sh" search <query> [--limit N] [--refresh]

fetch options:
  --full   Entire page as markdown (default).
  --body   Main article content only (strips nav/header/footer).
  --nav    Sidebar/navigation links as a markdown bullet list.

search options:
  --limit N   Max results to print (default 15).
  --refresh   Force a re-fetch of the search index instead of using the
              cached copy (cached for 1 day by default).

  -h, --help

Examples:
  bash "$SKILL_DIR/scripts/cxdocs.sh" search "table indexing"
  bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/ --body

Don't have the exact URL? Run `search` first, then feed a result URL into
`fetch`.

Requires a one-time, interactive `cxdocs-cli login` (Chrome + Duo SSO) run
by the user in their own terminal. This wrapper will tell you to do that if
no valid session is found — it will not attempt login itself.
USAGE
}

# --- shared: install + session handling -------------------------------------

# Multi-account SSH setups often alias github.com per identity (e.g.
# `Host github-cxepi` -> HostName github.com -> a specific IdentityFile),
# because `git@github.com` alone only carries one key. Prefer an alias
# whose Host name references the org, so `uv tool install` uses the SSH
# key that actually has access to CXEPI's private repos instead of
# whichever key answers plain `github.com` first.
detect_github_ssh_alias() {
  local ssh_config="$HOME/.ssh/config"
  [[ -f "$ssh_config" ]] || return 0

  local cur_aliases="" cur_hostname="" match=""
  local org_lc
  org_lc="$(printf '%s' "$CXDOCS_ORG" | tr '[:upper:]' '[:lower:]')"

  flush_block() {
    if [[ "$cur_hostname" == "github.com" ]]; then
      local a a_lc
      for a in $cur_aliases; do
        a_lc="$(printf '%s' "$a" | tr '[:upper:]' '[:lower:]')"
        case "$a_lc" in
          *"$org_lc"*) match="$a" ;;
        esac
      done
    fi
  }

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[[:space:]]*Host[[:space:]]+(.+)$ ]]; then
      flush_block
      cur_aliases="${BASH_REMATCH[1]}"
      cur_hostname=""
    elif [[ "$line" =~ ^[[:space:]]*HostName[[:space:]]+(.+)$ ]]; then
      cur_hostname="${BASH_REMATCH[1]}"
    fi
  done < "$ssh_config"
  flush_block

  [[ -n "$match" ]] && echo "$match"
}

CXDOCS_GIT_HOST="${CXDOCS_GIT_SSH_HOST:-}"
if [[ -z "$CXDOCS_GIT_HOST" ]]; then
  CXDOCS_GIT_HOST="$(detect_github_ssh_alias || true)"
fi
CXDOCS_GIT_HOST="${CXDOCS_GIT_HOST:-github.com}"
CXDOCS_REPO="${CXDOCS_INSTALL_SOURCE:-git+ssh://git@${CXDOCS_GIT_HOST}/${CXDOCS_ORG}/${CXDOCS_REPO_PATH}}"

ensure_cxdocs_cli_installed() {
  if command -v cxdocs-cli >/dev/null 2>&1; then
    return 0
  fi

  echo "cxdocs-cli not found on PATH. Installing via uv from $CXDOCS_REPO ..." >&2
  if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not installed. Install it from https://docs.astral.sh/uv/ then retry." >&2
    exit 1
  fi

  if ! uv tool install "$CXDOCS_REPO" >&2; then
    echo "ERROR: install failed from $CXDOCS_REPO." >&2
    echo "If you use multiple GitHub SSH identities, set CXDOCS_GIT_SSH_HOST to the Host alias in ~/.ssh/config that has access to the ${CXDOCS_ORG} org (or set CXDOCS_INSTALL_SOURCE to a full git+ssh URL) and retry." >&2
    exit 1
  fi

  # Playwright's bundled Chromium is only needed on Linux/WSL; macOS/Windows
  # use the system Chrome browser (channel="chrome") for the login flow.
  case "$(uname -s)" in
    Linux)
      echo "Linux detected — installing Playwright Chromium for cxdocs-cli login..." >&2
      uv tool run --from cxdocs-cli playwright install --with-deps chromium >&2
      ;;
  esac

  if ! command -v cxdocs-cli >/dev/null 2>&1; then
    echo "ERROR: cxdocs-cli install completed but the binary is still not on PATH. Check your uv tool shim directory (usually ~/.local/bin)." >&2
    exit 1
  fi
}

no_session_hint() {
  echo "ERROR: no valid cxdocs-cli session. Ask the user to run 'cxdocs-cli login' themselves in their own terminal (interactive Chrome + Duo SSO), then retry." >&2
}

# --- fetch --------------------------------------------------------------

cmd_fetch() {
  local url="" mode="--full"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --full|--body|--nav) mode="$1"; shift ;;
      -*) echo "ERROR: unknown flag: $1" >&2; exit 2 ;;
      *)
        if [[ -n "$url" ]]; then
          echo "ERROR: unexpected extra argument: $1" >&2
          exit 2
        fi
        url="$1"
        shift
        ;;
    esac
  done

  if [[ -z "$url" ]]; then
    echo "ERROR: missing <url>." >&2
    usage >&2
    exit 2
  fi

  ensure_cxdocs_cli_installed

  local stderr_file rc
  stderr_file="$(mktemp)"
  set +e
  cxdocs-cli fetch "$url" "$mode" 2>"$stderr_file"
  rc=$?
  set -e

  if [[ "$rc" -ne 0 ]]; then
    cat "$stderr_file" >&2
    grep -qi "cxdocs-cli login" "$stderr_file" && no_session_hint
    rm -f "$stderr_file"
    exit "$rc"
  fi
  rm -f "$stderr_file"
}

# --- search ---------------------------------------------------------------

cache_is_fresh() {
  local ttl="${CXDOCS_SEARCH_CACHE_TTL_SECONDS:-86400}"
  [[ -f "$CACHE_FILE" ]] || return 1
  local age now mtime
  now="$(date +%s)"
  mtime="$(stat -f %m "$CACHE_FILE" 2>/dev/null || stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)"
  age=$(( now - mtime ))
  [[ "$age" -lt "$ttl" ]]
}

refresh_search_cache() {
  ensure_cxdocs_cli_installed
  mkdir -p "$CACHE_DIR"
  local tmp_file stderr_file rc
  tmp_file="$(mktemp)"
  stderr_file="$(mktemp)"

  # mkdocs-material's search_index.json is JSON, not an HTML doc page —
  # `cxdocs-cli fetch` always runs content through html2text (built for
  # HTML), which mangles JSON escape sequences. Go around it and use
  # cxdocs-cli's own auth/session-cookie machinery directly to make one raw
  # GET, same as `fetch` does internally before its markdown step.
  set +e
  uv tool run --from cxdocs-cli python3 -c '
import sys
from cxdocs_cli.auth import get_auth_manager
from cxdocs_cli.client import build_client
from cxdocs_cli.config import get_config
from cxdocs_cli.exceptions import AuthenticationError, SessionExpiredError

url = sys.argv[1]
try:
    config = get_config()
    manager = get_auth_manager(config)
    cookie = manager.get_session_cookie()
    with build_client(cookie, config) as client:
        resp = client.get(url)
        resp.raise_for_status()
        sys.stdout.write(resp.text)
except SessionExpiredError as exc:
    print(str(exc), file=sys.stderr)
    print("Run '"'"'cxdocs-cli login'"'"' to re-authenticate.", file=sys.stderr)
    sys.exit(1)
except AuthenticationError as exc:
    print(f"Authentication error: {exc}", file=sys.stderr)
    print("Run '"'"'cxdocs-cli login'"'"' to authenticate.", file=sys.stderr)
    sys.exit(1)
' "${CXDOCS_BASE_URL}/search/search_index.json" > "$tmp_file" 2>"$stderr_file"
  rc=$?
  set -e

  if [[ "$rc" -ne 0 ]]; then
    cat "$stderr_file" >&2
    grep -qi "cxdocs-cli login" "$stderr_file" && no_session_hint
    rm -f "$tmp_file" "$stderr_file"
    exit "$rc"
  fi

  rm -f "$stderr_file"
  mv "$tmp_file" "$CACHE_FILE"
}

cmd_search() {
  local query="" limit=15 refresh=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --limit)
        limit="${2:-}"
        [[ -n "$limit" ]] || { echo "ERROR: --limit needs a value." >&2; exit 2; }
        shift 2
        ;;
      --refresh) refresh=1; shift ;;
      -*) echo "ERROR: unknown flag: $1" >&2; exit 2 ;;
      *)
        if [[ -n "$query" ]]; then query="$query $1"; else query="$1"; fi
        shift
        ;;
    esac
  done

  if [[ -z "$query" ]]; then
    echo "ERROR: missing <query>." >&2
    usage >&2
    exit 2
  fi

  if [[ "$refresh" -eq 1 ]] || ! cache_is_fresh; then
    refresh_search_cache
  fi

  BASE_URL="$CXDOCS_BASE_URL" LIMIT="$limit" python3 -c '
import json
import os
import sys

query = sys.argv[1]
base_url = os.environ["BASE_URL"]
limit = int(os.environ["LIMIT"])

with open(sys.argv[2]) as f:
    index = json.load(f)

terms = [t.lower() for t in query.split() if t]

def score(doc):
    title = (doc.get("title") or "").lower()
    text = (doc.get("text") or "").lower()
    s = 0
    for t in terms:
        if t in title:
            s += 100
        if t in text:
            s += 1
    return s

scored = [(score(d), d) for d in index.get("docs", [])]
scored = [(s, d) for s, d in scored if s > 0]
scored.sort(key=lambda pair: pair[0], reverse=True)

if not scored:
    print("No matches. Try fewer/different terms.", file=sys.stderr)
    sys.exit(1)

seen = set()
count = 0
for _, d in scored:
    loc = d.get("location") or ""
    url = base_url.rstrip("/") + "/" + loc.lstrip("/")
    if url in seen:
        continue
    seen.add(url)
    title = d.get("title") or "(untitled)"
    print(f"{title} -- {url}")
    count += 1
    if count >= limit:
        break
' "$query" "$CACHE_FILE"
}

# --- dispatch ---------------------------------------------------------------

SUBCOMMAND="${1:-}"
[[ $# -gt 0 ]] && shift

case "$SUBCOMMAND" in
  fetch) cmd_fetch "$@" ;;
  search) cmd_search "$@" ;;
  -h|--help|"") usage; [[ "$SUBCOMMAND" == "" ]] && exit 2 || exit 0 ;;
  *) echo "ERROR: unknown subcommand: $SUBCOMMAND" >&2; usage >&2; exit 2 ;;
esac
