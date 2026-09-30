# sb Docs

Documentation for the sb (Second Brain) repository. Start with the
top-level `README.md` and `PENDING.md`, then use this set for depth.

## This doc set

| Doc | Covers |
|---|---|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Install, run sb-core, launchd, wire MCP into harnesses, run the web dashboard |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Process model, transports, data model, signal ledger, skills, daily rituals, security posture |
| [SERVICES.md](./SERVICES.md) | Per-service purpose, storage, entry points, MCP tools, tests |
| [MCP_TOOLS.md](./MCP_TOOLS.md) | Full MCP tool reference, grouped by service, read/write classification |
| [WEB_DASHBOARD.md](./WEB_DASHBOARD.md) | Dashboard stack, routes, Vite proxy config, shortcuts, dev commands |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Tests, lint, launchd ops, debugging, skill authoring |

## Existing docs (not duplicated here)

| Doc | Covers |
|---|---|
| [design/](./design/) | `DESIGN_SYSTEM.md`, `COMPONENTS.md`, `DESIGN_BRIEF.md`, `SCREENS.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `mockups/today-view.html` |
| [status/](./status/) | Historical Phase 0/1 snapshots and design decisions |

Individual service READMEs: `services/todos/README.md`,
`services/jira/README.md` (no README for `services/core` or
`services/webex` — see `docs/SERVICES.md` for their coverage).
