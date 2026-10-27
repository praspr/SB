# Web Dashboard

`sb/web` is the local dashboard: Vite + React + TypeScript + Tailwind, dark-first
Linear-inspired UI. Dev server runs at `http://localhost:5173/_ui/`.

## Hosting

- **Dev**: `npm run dev` → Vite at `http://localhost:5173/_ui/`, reaching
  sb-core through the Vite proxies below.
- **Production (same-origin)**: `npm run build` emits `web/dist/`, which the
  sb-core FastAPI process serves at `http://127.0.0.1:8787/_ui/`. No separate
  server or port — the existing `com.praspr.sb` launchd job hosts the UI and
  the MCP transports in the same process. The SPA is reached under the
  uncommon `/_ui` prefix (deep client routes fall back to `index.html`).

In production the browser is same-origin with sb-core, so the app calls the
MCP at `/mcp` directly and reaches the usage proxies via same-origin FastAPI
routes (`/proxy/claudegate/*`, `/proxy/cursor/*`) instead of the Vite dev
proxies. The MCP endpoint is environment-aware in `web/src/lib/mcp.ts`
(`/proxy/mcp` in dev, `/mcp` in prod); Vite `base` and the React Router
`basename` are both `/_ui`.

## Stack

- Vite 5, React 18, TypeScript 5
- Tailwind CSS 3 for styling
- `@tanstack/react-query` for data fetching/caching against the MCP proxy
- `react-router-dom` for routing
- `zustand` for local UI state
- `framer-motion` for animation primitives
- Radix UI primitives (`dialog`, `popover`, `tabs`, `slot`) under `src/components/ui/`
- Test runner: Vitest (`npm run test`) — every test file uses
  `renderToStaticMarkup` + string assertions (no `@testing-library/react`,
  no `fireEvent`); pages that need interactive-state coverage export a pure
  presentational "View" component (e.g. `ReportsView`, `AttentionView`,
  `SchedulesTab`) that tests render directly with explicit props

See `web/package.json` for exact dependency versions.

## Routes

Defined in `web/src/router.tsx`, rendered inside `web/src/components/layout/AppShell.tsx`.

| Route | Page component | Data | Status |
|---|---|---|---|
| `/` — Landing | `web/src/pages/LandingPage.tsx` | Usage tiles · charts · Morning Brief dialog · cited local chat | live |
| `/attention` | `web/src/pages/AttentionPage.tsx` | Ranked Webex mentions/DMs/replies-to-me (`webexAttentionFiltered`), one-click log-to-ledger | live after sign-in and sync |
| `/goals` | `web/src/pages/GoalsPage.tsx` | DB-backed goals by tier, alignment heatmap, drift alerts | live |
| `/reports` | `web/src/pages/ReportsPage.tsx` | Daily/Weekly/Monthly/Query ledger reports + Today/Wrap/Standup sub-tabs; Post-to-Webex + Email-draft actions | live |
| `/ledger` | `web/src/pages/LedgerPage.tsx` | Append-only ledger table + timeline, full-text search | live |
| `/proposals` | `web/src/pages/ProposalsPage.tsx` | Pending CHANGELOG / meeting-note proposals, approve/reject | live |
| `/skills` | `web/src/pages/SkillsPage.tsx` | Indexed project and system skills | live |
| `/signals` | `web/src/pages/SignalsPage.tsx` | Local evidence ledger and adapter state | live |
| `/todos` | `web/src/pages/TodosPage.tsx` | sb-todos SQLite, goal/JIRA/recurrence pickers, bulk-JIRA-import action | live |
| `/jira` | `web/src/pages/JirasPage.tsx` | Pull-only JIRA mirror, plus Track JIRA from a pasted key/link | live |
| `/meetings` | `web/src/pages/MeetingsPage.tsx` | Mirrored Webex meetings, a pre-meeting context card (auto-shows within 15 min of start), "Propose notes" on past meetings | live after sign-in and sync |
| `/webex` | `web/src/pages/WebexPage.tsx` | Filtered attention (DMs + mentions only), spaces with mute/unmute, cited space summaries | live after sign-in and sync |

**Retired routes**: `/today`, `/wrap`, `/standup` (folded into `/reports`
sub-tabs during Phase 1.5) and `/status` (folded into the Settings popover's
Diagnostics tab during Phase 2). Do not re-add `StatusPage.tsx`,
`TodayPage.tsx`, `WrapPage.tsx`, or `StandupPage.tsx` to the router — they no
longer exist.

Supporting component directories: `web/src/components/layout/` (shell,
sidebar, top bar, Settings popover, Schedules tab), `web/src/components/landing/`
(usage stats, insights, chat panel, Morning Brief), `web/src/components/attention/`
(`AttentionRow` — shows a small "reply" chip for `is_reply_to_me` items),
`web/src/components/tasks/` (todo add/list/row, goal picker, JIRA ref
autocomplete, recurrence picker), `web/src/components/jira/` (filter bar,
track-jira form, ticket list/row), `web/src/components/webex/` (mention
badge, space row with mute toggle, message preview), `web/src/components/meetings/`
(pre-meeting card), `web/src/components/reports/` (`ReportViewer`,
`WebexPostButton` — the Post-to-Webex popover and Email-draft mailto
builder), `web/src/components/ledger/` (`LedgerTable`, `LedgerTimeline`),
`web/src/components/proposals/` (`ProposalRow`), `web/src/components/palette/`
(`CommandPalette`, `paletteCommands.ts`, `AttachRefDialog`), `web/src/components/shared/`
(empty state, skeleton row).

Data/query logic lives under `web/src/lib/`: `mcp.ts` (the MCP JSON-RPC
client), `queries.ts` + `queries.<domain>.test.ts`, `ledger.ts`, `reports.ts`,
`triage.ts`, `goals.ts`, `schedules.ts`, `webex-post.ts`, `webex-mute.ts`,
`bulk-jira.ts`, `url-hints.ts`, `jira-page.ts`, `skills.ts`, `status.ts`,
`jira-utils.ts`, `chat.ts`, `store.ts`, `system-clock.ts`, `usage-pie.ts`,
`mock-data.ts`.

## Command palette

`web/src/components/palette/CommandPalette.tsx` (⌘K). Three modes, mutually
exclusive based on the query string:

1. **Normal search** (default) — fans out to ledger/todos/JIRA/Webex
   attention/skills/report-citation queries and groups results by source.
2. **Slash commands** — when the query starts with `/`, shows a **Commands**
   group matching the typed prefix (pure matching logic in
   `paletteCommands.ts::matchSlashCommands`): `/plan` → `/reports?template=daily`,
   `/wrap` → `/reports?template=wrap`, `/standup` → `/reports?template=standup`,
   `/brief` → runs `reportDaily()` inline and shows the markdown in a Dialog,
   `/goals` → `/goals`, `/attention` → `/attention`, `/ledger <q>` →
   `/ledger?q=<encoded q>`. A hint line appears below the input when the
   query starts with `/` but matches no command.
3. **URL smart handler** — when the query matches `^(https?://|webexteams://|file://)`,
   calls `parseUrlHint` and renders one classified result: a JIRA browse
   link offers "Track JIRA `<key>`" (calls the `track_jira` tool directly via
   `callTool`, then navigates to `/jira?q=<key>` regardless of outcome); a
   Webex link opens `webexteams://...` in a new tab; a GitHub PR or `file://`
   link opens a small `AttachRefDialog` (project picker + summary, pre-filled
   ref) that calls `ledgerLog` on submit; anything else falls back to the
   same attach-ref dialog with `kind="generic"`.

`ReportsPage.tsx` reads `?template=<name>` on mount to preselect the active
report template, which is what makes the `/plan`/`/wrap`/`/standup` slash
commands land on the right sub-tab.

## Settings popover

`web/src/components/layout/SettingsPopover.tsx`, opened from the gear icon
at the bottom of the sidebar. Five tabs:

| Tab | Content |
|---|---|
| Connections | Live `SETTING_CHECKS` (`web/src/lib/settings-checks.ts`) — MCP reachability, claudegate, Cursor cookie, etc. |
| Diagnostics | `fetchCoreStatus()` — database readiness, schema version, service version, tool/prompt/resource counts (replaces the retired `/status` page) |
| Projects | `ledgerProjects()` list + an inline enroll form (`ledgerRegisterProject`) |
| Sessions | `ledgerSessions(20)` — recent ledger session ids, grouped by project |
| Schedules | `listScheduledRituals()` table (name/ritual/cron/enabled/last run/status, per-row Delete) + an inline Add-schedule form (`addScheduledRitual`); presentational content lives in `SchedulesTab.tsx` so it's testable without opening the Radix popover |

## Morning Brief

`web/src/components/landing/MorningBrief.tsx`, shown on the Landing page.
Gated by `localStorage` (a per-day key so it shows at most once per calendar
day) and calls `reportDaily(today)` on mount to render the daily report in a
Dialog. `onOpenChange` is wired so Esc, clicking the backdrop, or the X
button all close it correctly (an earlier bug left the dialog only
closeable by its own internal button).

## Vite proxy configuration

Defined in `web/vite.config.ts`:

| Path prefix | Target | Purpose |
|---|---|---|
| `/proxy/mcp` | `http://127.0.0.1:8787` (rewritten, strips prefix, `/mcp` appended) | sb-core MCP endpoint |
| `/proxy/claudegate` | `http://localhost:9999` | GitHub Copilot usage proxy (Anthropic-compatible) |
| `/proxy/cursor` | `https://cursor.com` | Cursor usage proxy; dev server injects the `WorkosCursorSessionToken` cookie read from Cursor.app's local `state.vscdb` (`web/vite/cursor-auth.ts`) — the browser never sees the token |

These proxies only exist in the Vite dev server. In **production** the UI is
served same-origin by sb-core, which provides the equivalent FastAPI routes
(`services/core/src/sb_core/main.py`):

| Route | Target | Purpose |
|---|---|---|
| `/_ui`, `/_ui/`, `/_ui/{path}` | `web/dist/` (`settings.web_dist_path`, env `SB_WEB_DIST_PATH`) | Serves the built SPA; unknown subpaths fall back to `index.html`, missing build returns a 503 placeholder |
| `/mcp` | in-process FastMCP | MCP endpoint, called directly (no `/proxy/mcp` in prod) |
| `/proxy/claudegate/{path}` | `http://localhost:9999` | GitHub Copilot usage passthrough (httpx) |
| `/proxy/cursor/{path}` | `https://cursor.com` | Cursor usage passthrough; the `WorkosCursorSessionToken` cookie is built server-side by `sb_core/cursor_auth.py` (stdlib port of `cursor-auth.ts`), reading `state.vscdb` read-only, caching 5 min, failing soft — the browser never sees the token |

## Keyboard shortcuts

- `⌘K` — opens the command palette (`web/src/components/palette/CommandPalette.tsx`)
- `⌘N` — jumps to `/todos` and focuses the quick-add input

## Design tokens and component catalog

Do not duplicate here — see:

- `sb/docs/design/DESIGN_SYSTEM.md` — token spec
- `sb/docs/design/COMPONENTS.md` — component catalog
- `sb/docs/design/DESIGN_BRIEF.md`, `sb/docs/design/SCREENS.md`, `sb/docs/design/ARCHITECTURE.md`
- `sb/docs/design/mockups/today-view.html` — fully rendered HTML mockup

## Dev commands

```bash
cd sb/web
npm install         # first time only
npm run dev         # http://localhost:5173
npm run build        # tsc -b && vite build → web/dist/
npm run preview      # serve the production build locally
npm run lint         # tsc --noEmit
npm run test         # vitest run
```

Build output goes to `web/dist/`. There is no configured production server
for the built assets in this repo — the dashboard is intended to be run via
`npm run dev` locally.
