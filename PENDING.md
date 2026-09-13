# PENDING — sb roadmap

Everything the codebase does NOT currently do, organized by "how much work"
and "how much value." Reasonable order top-to-bottom, but skip freely.

Legend: **S** ≈ ½ day · **M** ≈ 1–2 days · **L** ≈ 3+ days

---

## High-value, small effort

### 1. Wire the "Refresh from Atlassian" button end-to-end (**S**)
- `sb-jira` already has the `sync_jira` tool and the `POST /api/jira/sync`
  endpoint. Both no-op safely without a token.
- What's missing: nothing on the server side. The web app's Refresh button
  already calls it. Just need to:
  - Store an Atlassian API token in Keychain (`sb secret set jira.token`
    — but no `sb` CLI exists yet, so use `security add-generic-password`
    or a small keyring helper)
  - Verify the button now returns updated_count > 0

### 2. Persist sync state / show "last synced N minutes ago" on JIRA page (**S**)
- `sb-jira`'s `/api/jira/status` already returns `last_sync_at`. Just isn't
  displayed in the UI.
- Add a small pill under the JIRAs page header.

### 3. Todos: add/edit fields (due date, priority, tags) in the web UI (**S**)
- The QuickAddInput only supports title. sb-todos already supports every
  field. Extend the AddTodoDialog + row row-edit affordance.

### 4. Command palette: fuzzy-search todos + JIRA tickets (**S**)
- Palette currently only has fixed actions. Add live search: type a query,
  see matching todos and JIRA tickets, Enter opens them.

---

## Bigger scope, more value

### 5. Meetings adapter — real data via Outlook JXA (**M**)
- Deferred original Phase 3.
- Outlook 16.112 ships a 168 KB `.sdef` AppleScript dictionary — zero-auth
  reads via `osascript` if you're on legacy Outlook.
- Fallback: Microsoft Graph device-code flow.
- Deliverable: new `sb/services/meetings/` service, `/proxy/meetings` proxy,
  Meetings page shows real events, Landing page's "Meetings today" section
  works.

### 6. Webex adapter — DMs + @mentions + spaces (**M**)
- Deferred original Phase 3.
- Cisco Webex REST at `webexapis.com/v1`. Personal Access Tokens expire in
  12 h — for background sync you'd need a Webex Integration with OAuth
  refresh.
- Deliverable: `sb/services/webex/` service, Webex page shows real data.

### 7. Menu-bar app + PWA (**M**)
- Designed but not built. See `sb/docs/design/SCREENS.md` for the spec.
- Menu bar: tiny popover with today's top 3 todos + a "Wrap now" action.
  Tauri or Electron.
- PWA: `sb/web` gains a manifest + installable-to-dock experience.

### 8. Cursor session cookie config UI (**S**)
- If the auto-read from `state.vscdb` ever fails (e.g. Cursor.app not signed
  in), currently the tile just says "Not configured."
- Add a small Settings page where the user can paste a cookie manually,
  stored in a local file readable only by the user (or Keychain).

---

## The big one

### 9. Full sb chief-of-staff Python backend (Phase D from the plan) (**L**)
- Would resurrect the original vision: `sb plan` / `sb wrap` / `sb standup`
  as a daily loop with LLM synthesis + evidence citation.
- ~8 000 lines of Python across 17 modules (config, models, store, adapters,
  brain/llm, brain/rank, brain/plan, brain/wrap, mcp/server, cli, tests).
- Specs exist verbatim in `sb/docs/status/` and `sb/docs/design/`.
- Blocks: nothing technical. Deferred because we opted to build the todos +
  JIRA MCPs first and see how they feel.
- If you do this, wire `sb-todos` into it as the task-storage MCP (already
  built to be consumed).

---

## Nice-to-haves (unranked)

- **JSON schema export** for `sb-todos` REST + MCP — auto-generate an OpenAPI
  doc so other tools can consume it.
- **Search endpoint on sb-jira** — `sb-jira` currently filters client-side.
  A dedicated `?q=` search over ticket bodies (not just title) would be
  useful.
- **Cursor rules file** (`.cursor/rules/sb.mdc`) with usage examples for the
  MCP tools so Cursor auto-suggests them.
- **Todos: recurrence** — SQLite schema doesn't model repeating tasks.
- **Bulk import** — a one-liner to import all assigned JIRA tickets into
  sb-todos as manual copies for triage.
- **Session cookie cache TTL config** — Cursor cookie is cached 5 min; the
  Copilot proxy has its own 60 s cache. Move both to config.
- **Test coverage report** — sb-todos: 27 tests, sb-jira: 21 tests, web: none.
  Add Vitest/React Testing Library for the web app.
- **CI** — nothing runs on git push. GitHub Actions running tsc, pytest, and
  the FastAPI TestClients would catch regressions.
- **Signals ledger + evidence-based wrap** — the missing chief-of-staff piece
  (see item 9).
- **Goals + ranker in the web app** — a page showing tiered goals and their
  keyword-alignment scores against pending todos.
- **Proposals inbox UI** — the sb backend design queues "propose, don't act"
  suggestions (JIRA transitions, replies, CHANGELOG edits). No UI yet.

---

## Rejected / explicitly out of scope

- **Writing back to Atlassian.** JIRA is read-only per user decision. The
  `sync_jira` tool pulls only.
- **Rebuilding on top of the old Python `sb` backend** that Phase 0/1
  produced — that code was lost from disk and rebuilding it fresh is item 9
  above rather than a restoration.
- **Cloud sync / multi-machine.** Everything is deliberately local.

---

## Known issues / rough edges

- **Meetings page** shows mock data. Landing page's "Meetings today" too.
- **Webex page** shows mock data.
- **Web app has zero unit tests.**
- **`sb-todos` idempotent upsert** is only exercised when `external_ref` is
  provided — no test yet for the "same ref twice" path from HTTP.
- **launchd services** use `KeepAlive=true` — if the process crashes rapidly
  in a boot loop, it will keep respawning. Add throttle if that ever bites.
- **CORS** on both services is currently limited to `http://localhost:5173`.
  If you serve the web app on a different port, add it to the allow list.
- **`Rebuild sb backend`** from `docs/status/` — those docs describe a
  system that no longer exists on disk. They're accurate for the design but
  the code needs to be rebuilt if you want that stack.

---

Ordering suggestion if you asked me to pick: **1 → 2 → 3 → 5 → 6 → 4 → 7 → 8 → 9**.
