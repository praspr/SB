#!/usr/bin/env bash
#
# sb-serve — build the web dashboard and run sb-core so the MCP transports
# and the dashboard are served from one process, same-origin.
#
# The built SPA is served by sb-core at  http://HOST:PORT/_ui/  and the MCP
# at /mcp — no separate dev server or port. This mirrors the production
# launchd setup but is meant to be run by hand, frequently, during dev.
#
# Usage:
#   scripts/sb-serve.sh                 # build web/dist, then run sb-core on 127.0.0.1:8787
#   scripts/sb-serve.sh --no-build      # skip the npm build (serve the existing web/dist)
#   scripts/sb-serve.sh --port 9123      # bind a different port
#   scripts/sb-serve.sh --host 0.0.0.0   # bind a different host (default 127.0.0.1)
#   scripts/sb-serve.sh --open           # open the dashboard in the browser once it is up
#
# Env overrides:
#   SB_HOST, SB_PORT        same as --host / --port
#   SB_WEB_DIST_PATH        directory sb-core serves at /_ui (default <repo>/web/dist)
#
set -euo pipefail

# ── Resolve the repo root from this script's location ───────────────────────
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
CORE_DIR="${REPO_ROOT}/services/core"
WEB_DIR="${REPO_ROOT}/web"
DIST_DIR="${SB_WEB_DIST_PATH:-${WEB_DIR}/dist}"

HOST="${SB_HOST:-127.0.0.1}"
PORT="${SB_PORT:-8787}"
DO_BUILD=1
DO_OPEN=0

# ── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) DO_BUILD=0; shift ;;
    --open) DO_OPEN=1; shift ;;
    --host) HOST="${2:?--host needs a value}"; shift 2 ;;
    --port) PORT="${2:?--port needs a value}"; shift 2 ;;
    -h|--help)
      sed -n '2,/^set -euo/{/^set -euo/d; s/^# \{0,1\}//; p;}' "${BASH_SOURCE[0]}"
      exit 0 ;;
    *) echo "sb-serve: unknown arg '$1' (try --help)" >&2; exit 2 ;;
  esac
done

log() { printf '\033[1;34m[sb-serve]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[sb-serve] %s\033[0m\n' "$*" >&2; exit 1; }

command -v uv >/dev/null 2>&1 || die "uv not found on PATH (expected ~/.local/bin/uv)"

# ── Build the dashboard ─────────────────────────────────────────────────────
if [[ "${DO_BUILD}" -eq 1 ]]; then
  command -v npm >/dev/null 2>&1 || die "npm not found on PATH"
  log "building dashboard → ${WEB_DIR}/dist"
  if [[ ! -d "${WEB_DIR}/node_modules" ]]; then
    log "installing web deps (first run)"
    ( cd "${WEB_DIR}" && npm install )
  fi
  ( cd "${WEB_DIR}" && npm run build )
else
  log "skipping build (--no-build)"
fi

if [[ ! -f "${DIST_DIR}/index.html" ]]; then
  die "no built dashboard at ${DIST_DIR}/index.html — run without --no-build, or set SB_WEB_DIST_PATH"
fi

# ── Optionally open the dashboard once the server answers ───────────────────
if [[ "${DO_OPEN}" -eq 1 ]]; then
  ( UI_URL="http://${HOST}:${PORT}/_ui/"
    for _ in $(seq 1 40); do
      if curl -fsS -o /dev/null "http://${HOST}:${PORT}/health" 2>/dev/null; then
        command -v open >/dev/null 2>&1 && open "${UI_URL}"
        break
      fi
      sleep 0.5
    done ) &
fi

# ── Run sb-core (serves /mcp, /sse, /health, and /_ui) ──────────────────────
export SB_WEB_DIST_PATH="${DIST_DIR}"
log "serving sb-core on http://${HOST}:${PORT}  (dashboard: /_ui/ · mcp: /mcp)"
exec uv run --project "${CORE_DIR}" \
  uvicorn sb_core.main:app --host "${HOST}" --port "${PORT}"
