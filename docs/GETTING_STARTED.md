# Getting Started

## Prerequisites

- macOS
- Python 3.13+ and [`uv`](https://docs.astral.sh/uv/) at `~/.local/bin/uv`
- Node 20+ and npm

## Repo layout at a glance

```
sb/
├── web/                    React + TypeScript dashboard (Vite, port 5173)
├── services/
│   ├── core/                sb-core — unified local MCP process (port 8787)
│   ├── todos/                sb-todos — MCP library mounted in-process, SQLite-backed
│   ├── jira/                 sb-jira — read-only MCP library mounted in-process
│   ├── webex/                sb-webex — Webex client library mounted in-process
│   └── cli/                  sb-cli — `sb` command-line client
├── docs/
│   ├── status/               Phase 0/1 status snapshots
│   ├── design/               UI design brief, tokens, components, HTML mockup
│   └── (this doc set)
├── harness/skills/           SKILL.md files indexed by sb-core
├── README.md                 Top-level overview
└── PENDING.md                What's next / not built yet
```

See `README.md` for the authoritative service/port table and architecture diagram.

## Bootstrapping the core service

From the repo root:

```bash
cd sb/services/core
uv sync --group dev
uv run uvicorn sb_core.main:app --host 127.0.0.1 --port 8787
```

This starts the single unified MCP process. Todos and JIRA tools are mounted
in-process (no separate servers to start). Webex tools call the hosted MCP
directly once you sign in (see below).

## Installing the launchd job

`com.praspr.sb` is the primary sb launchd job. Two supporting jobs ship
alongside it: `com.praspr.sb-morning-open` (opens the dashboard once a day)
and `com.praspr.sb-scheduler` (ticks `run_due_schedules` every 5 minutes).
Run these from the repo root:

```bash
# Install and load the unified service
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist

# Install the morning-open and scheduler jobs
cp services/core/launchd/com.praspr.sb-morning-open.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-scheduler.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-morning-open.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-scheduler.plist

# Retire the standalone todos and JIRA jobs (if present from an older setup)
launchctl bootout gui/$(id -u)/com.praspr.sb-todos || true
launchctl bootout gui/$(id -u)/com.praspr.sb-jira || true
rm -f ~/Library/LaunchAgents/com.praspr.sb-todos.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb-jira.plist

# Smoke
curl -s http://127.0.0.1:8787/health
```

See `services/core/launchd/README.md` for a job-by-job reference (labels,
intervals, log paths, and what each one's `ProgramArguments` actually runs).

### Restarting after a schema or tool change

Any time you pull new code that changes `sb_core`'s schema or mounted MCP
tools, restart the running process so it picks up the change:

```bash
launchctl kickstart -k gui/$(id -u)/com.praspr.sb
```

The morning-open and scheduler jobs never need a kickstart — they only shell
out to `curl`/`open`, not to the long-running Python process.

## Health check

```bash
curl -s http://127.0.0.1:8787/health
```

Returns a privacy-safe readiness summary: `status`, `version`, database
readiness/schema version, and tool/prompt/resource counts. It does not
contact Atlassian or Webex.

## Wiring MCP into your coding harness

One server, named `sb`, is the harness entry. Do not add separate
`sb-todos` / `sb-jira` network servers — they no longer exist standalone.

| Harness | Config file | Entry |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | one server named `sb` at `http://127.0.0.1:8787/mcp` |
| Claude Code | `~/.claude.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |
| OpenCode | `~/.config/opencode/opencode.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |

Remove only previous `sb-todos` / `sb-jira` entries; leave every other
server in those files untouched.

## Running the web dashboard

```bash
cd sb/web
npm install     # first time only
npm run dev     # → http://localhost:5173
```

The dashboard talks to sb-core through the Vite dev proxy at `/proxy/mcp`
(see `docs/WEB_DASHBOARD.md`). The dev server runs at
`http://localhost:5173/_ui/`.

## Optional: serve the dashboard from sb-core (no dev server)

sb-core can host the built dashboard same-origin, so the single launchd job
serves both the MCP transports and the UI in parallel — no `npm run dev`
needed:

```bash
cd sb/web
npm install     # first time only
npm run build   # emits web/dist/
```

Then open `http://127.0.0.1:8787/_ui/` (sb-core serves `web/dist/` under the
`/_ui` prefix). In this mode the UI calls the MCP at `/mcp` directly and the
Copilot/Cursor usage tiles go through sb-core's own `/proxy/claudegate/*` and
`/proxy/cursor/*` routes (the Cursor cookie is built server-side by
`sb_core/cursor_auth.py`). Override the served directory with
`SB_WEB_DIST_PATH` if `web/dist` lives elsewhere. If the build is missing,
`/_ui` returns a 503 placeholder and the MCP endpoints are unaffected.

## Optional: Webex sign-in

Webex tools are read-only (except one explicit posting action) and require a
one-time sign-in:

1. With sb-core running, open `http://127.0.0.1:8787/webex/login` in a browser.
2. Complete the hosted OAuth (PKCE) flow against
   `https://aicoding-mcp-webexapis.cisco.com/mcp/`.
3. Tokens are stored in the macOS Keychain under service `sb`. The browser
   never sees the token.
4. Call `sync_webex` (or use the `/webex` / `/meetings` pages) to pull a
   read-only mirror. On the **first** sync after signing in, `sync_webex`
   also captures your identity (email + display name, via the standard
   Webex REST API's `/people/me`) into a single-row `sb_webex_identity`
   table; this identity is what lets Attention detect replies to your own
   messages (`triage_kind: "reply-to-me"`). Later syncs reuse the cached
   identity — it is never re-fetched automatically.

## Optional: setting up scheduled rituals

Settings → Schedules lets you register a cron-triggered ritual (a subset of
5-field crontab syntax; see `services/core/src/sb_core/scheduler.py` for the
exact grammar). Example: run the wrap ritual every Friday at 16:00 local
time — name it, pick `wrap_day` from the ritual dropdown, and set the cron
field to `0 16 * * 5`. The `com.praspr.sb-scheduler` launchd job (see above)
must be installed and running for schedules to actually fire; the dashboard
only edits the schedule rows, it does not run a background timer itself.

## Optional: enrolling a project into the ledger

The ledger's project registry (`sb_project_registry`) is seeded with exactly
`ciq` and `sb` on first run. To track ledger entries for another repo, either:

- **Settings → Projects** in the dashboard — enter a project key, root path,
  and optional changelog path, then click Enroll.
- **`sb projects enroll`** from the CLI:

  ```bash
  cd sb/services/cli
  sb projects enroll --project myrepo --path /abs/path/to/myrepo --sync-mode dual
  ```

`--sync-mode dual` (the default) writes ledger entries to both SQLite and
that project's `CHANGELOG.md`; `sqlite-only` skips the file write.

## Optional: Atlassian token for JIRA sync

`sync_jira` only pulls from Atlassian into local markdown; it never writes
back. Store your API token in the macOS Keychain:

```bash
security add-generic-password -s sb -a jira.token -w '<token>'
```

(service `sb`, account/key `jira.token`) or set the `ATLASSIAN_API_TOKEN`
environment variable. Without a token, `sync_jira` returns an error entry and
changes nothing.

## Troubleshooting

- **Port 8787 already in use** — another sb-core instance (or launchd job)
  is likely running. Check `launchctl print gui/$(id -u)/com.praspr.sb` or
  `lsof -i :8787`.
- **launchd bootstrap failed** — confirm the plist was copied to
  `~/Library/LaunchAgents/com.praspr.sb.plist` and that no stale
  `com.praspr.sb-todos` / `com.praspr.sb-jira` jobs are still loaded
  (`launchctl bootout` them first).
- **`uv` not found** — install it per the [uv docs](https://docs.astral.sh/uv/)
  and confirm it resolves at `~/.local/bin/uv`.
- **`/health` returns `degraded`** — the SQLite database at
  `~/.local/share/sb/core.db` could not be opened; check permissions and
  parent directory existence (created automatically on first connection).
- **Web app can't reach MCP** — confirm sb-core is running on `:8787` before
  starting `npm run dev`; the Vite proxy fails silently if the target is down.
