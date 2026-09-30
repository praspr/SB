# Web Dashboard

`sb/web` is the local dashboard: Vite + React + TypeScript + Tailwind, dark-first
Linear-inspired UI. Dev server runs at `http://localhost:5173`.

## Stack

- Vite 5, React 18, TypeScript 5
- Tailwind CSS 3 for styling
- `@tanstack/react-query` for data fetching/caching against the MCP proxy
- `react-router-dom` for routing
- `zustand` for local UI state
- `cmdk` for the command palette, `framer-motion` for animation primitives
- Radix UI primitives (`dialog`, `popover`, `slot`) under `src/components/ui/`
- Test runner: Vitest (`npm run test`)

See `web/package.json` for exact dependency versions.

## Routes

Defined in `web/src/router.tsx`, rendered inside `web/src/components/layout/AppShell.tsx`.

| Route | Page component | Data | Status |
|---|---|---|---|
| `/` — Landing | `web/src/pages/LandingPage.tsx` | Usage tiles · todo/JIRA/signal charts · today's work · cited local chat | live |
| `/status` | `web/src/pages/StatusPage.tsx` | Unified MCP, database, tool/prompt/resource counts | live |
| `/skills` | `web/src/pages/SkillsPage.tsx` | Indexed project and system skills | live |
| `/signals` | `web/src/pages/SignalsPage.tsx` | Local evidence ledger and adapter state | live |
| `/today` | `web/src/pages/TodayPage.tsx` | Daily plan ritual | live |
| `/wrap` | `web/src/pages/WrapPage.tsx` | Wrap + CHANGELOG proposal approve/reject | live |
| `/standup` | `web/src/pages/StandupPage.tsx` | Standup bullet builder | live |
| `/todos` | `web/src/pages/TodosPage.tsx` | sb-todos SQLite (add + complete end-to-end) | live |
| `/jira` | `web/src/pages/JirasPage.tsx` | Pull-only JIRA mirror, plus Track JIRA from a pasted key/link | live |
| `/meetings` | `web/src/pages/MeetingsPage.tsx` | Mirrored Webex meetings and join links | live after sign-in and sync |
| `/webex` | `web/src/pages/WebexPage.tsx` | Attention, spaces, and cited space summaries | live after sign-in and sync |

Supporting component directories: `web/src/components/layout/` (shell,
sidebar, top bar), `web/src/components/landing/` (usage stats, insights,
chat panel), `web/src/components/tasks/` (todo add/list/row), `web/src/components/jira/`
(filter bar, track-jira form, ticket list/row), `web/src/components/webex/`
(mention badge, space row, message preview), `web/src/components/meetings/`,
`web/src/components/shared/` (command palette, empty state, skeleton row).

Data/query logic lives under `web/src/lib/` (`mcp.ts` — MCP client, `queries.ts`
and `queries.<domain>.test.ts`, `plan.ts`, `wrap.ts`, `standup.ts`, `signals.ts`,
`skills.ts`, `status.ts`, `jira-utils.ts`, `chat.ts`, `store.ts`, `mock-data.ts`).

## Vite proxy configuration

Defined in `web/vite.config.ts`:

| Path prefix | Target | Purpose |
|---|---|---|
| `/proxy/mcp` | `http://127.0.0.1:8787` (rewritten, strips prefix, `/mcp` appended) | sb-core MCP endpoint |
| `/proxy/claudegate` | `http://localhost:9999` | GitHub Copilot usage proxy (Anthropic-compatible) |
| `/proxy/cursor` | `https://cursor.com` | Cursor usage proxy; dev server injects the `WorkosCursorSessionToken` cookie read from Cursor.app's local `state.vscdb` (`web/vite/cursor-auth.ts`) — the browser never sees the token |

## Keyboard shortcuts

- `⌘K` — opens the command palette (`web/src/components/shared/CommandPalette.tsx`)
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
