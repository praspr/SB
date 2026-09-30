# sb Docs

Documentation for the sb (Second Brain) repository. Start with the
top-level `README.md`, then use this set for depth.

## This doc set

| Doc | Covers |
|---|---|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Install, run sb-core, launchd (core + morning-open + scheduler), wire MCP into harnesses, run the web dashboard, enroll a ledger project, set up scheduled rituals, sign in to Webex |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Process model, transports, data model, signal ledger, the append-only narrative ledger (redaction, sessions, dual-write), reports, comms triage, Webex thread-reply detection, goals registry, scheduler, skills, daily rituals, security posture |
| [SERVICES.md](./SERVICES.md) | Per-service purpose, storage, entry points, MCP tools (incl. every module added since Phase 0), and the new `sb-cli` package |
| [MCP_TOOLS.md](./MCP_TOOLS.md) | Full reference for all 76 MCP tools, grouped by submount, with read/write classification and citation formats |
| [WEB_DASHBOARD.md](./WEB_DASHBOARD.md) | Dashboard stack, full route table (incl. retired routes), command palette slash commands + URL handler, Settings popover tabs, Morning Brief, Vite proxy config, dev commands |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Running tests per service (incl. `sb-cli`), launchd kickstart, inspecting the ledger via sqlite3, adding a new report template, authoring a skill |

## Existing docs (not duplicated here)

| Doc | Covers |
|---|---|
| [design/](./design/) | `DESIGN_SYSTEM.md`, `COMPONENTS.md`, `DESIGN_BRIEF.md`, `SCREENS.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `mockups/today-view.html` |
| [status/](./status/) | Historical Phase 0/1 snapshots and design decisions |

Individual service READMEs: `services/todos/README.md`,
`services/jira/README.md`, `services/cli/README.md` (no README for
`services/core` or `services/webex` — see `docs/SERVICES.md` for their
coverage).
