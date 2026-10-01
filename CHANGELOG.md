# Changelog

## Unreleased

### Changed

- Migrate the pull-only Atlassian search client to the enhanced `/rest/api/3/search/jql` endpoint with token pagination, and align JIRA ordering, statuses, and last-sync metadata with the local markdown mirror.
- Reconcile the working tree before the unified MCP rollout. Baseline before Step 1: todos 18 passed, JIRA 14 passed, web MCP client 5 passed, and `tsc --noEmit` clean. The core suite is not green; unfinished ritual tests stay out of the active set until their step.

- Cut over login startup to the single `com.praspr.sb` launchd job and one `sb` MCP entry at `/mcp` in each harness. The standalone todos and JIRA jobs are retired. Startup now restores skill prompts and resources from the stored index, so they survive a restart.

### Added

- Redesign Today as a minimal daily focus view and Todos as a searchable, sortable, grouped productivity list with at-a-glance counts.
- Show Copilot and Cursor usage as compact pie charts in the top bar, with the full quota details on hover, next to the system date and time.
- Add prefilled, idempotent todo creation from JIRA rows, Webex attention items, and meeting todo proposals.
- Add JIRA untracking controls that stop future refreshes while retaining the local markdown mirror.
- Add hourly JIRA and 15-minute Webex pull schedules, evaluated every five minutes inside the existing sb-core process.
- Add Track JIRA on the JIRA page. A key or Cisco browse link is fetched read-only, written to the local mirror, and kept across assigned-issue syncs until it is untracked.
- Add a read-only Webex mirror on the unified MCP. Sign-in uses the hosted `webexapis` MCP with PKCE, tokens stay in the keychain, and sync only calls tools that read meetings, spaces, and message previews. The Meetings and Webex pages, landing attention count, daily plan, standup, and `ask_sb` citations use that local mirror.
- Add compact landing-page charts for todo completion, JIRA status, and signal sources, with drill-down links to filtered views.
- Add a read-only `ask_sb` MCP tool and landing-page chat grounded in bounded local todos, JIRA tickets, and signals. Answers use validated citations and fall back deterministically when the LLM is unavailable or returns unsupported claims.
- Scaffold `sb-core` on `127.0.0.1:8787` with a metadata-only SQLite schema, `system_status`, `/health`, and a `/status` page. Domain REST routes stay absent. Launchd plist is prepared; login cutover is documented and not applied.
- Mount the eight todo tools in-process on the same MCP, with a fresh SQLite connection per call, and point the Todos UI at that client. The standalone todos REST app and launchd plist are removed from the repo.
- Mount the four pull-only JIRA tools on the same MCP and point the JIRA page at that client. Health does not probe Atlassian. The standalone JIRA REST app and launchd plist are removed from the repo.
- Index `SKILL.md` files from allow-listed project, Cursor, Claude, and configured roots, and expose them as MCP tools, prompts, and resources plus a Skills page. Content is identified with SHA-256. Symlinks that leave a root are ignored.
- Add changelog, git, todo, and local JIRA signal adapters with `sync_adapters`, `sync_status`, and `search_signals`, and a Signals page that cites `[signal:N]`.
- Add deterministic daily planning (`plan_day`, `get_day`, `get_goals`, `get_roots`, `whoami`) that writes plan columns without overwriting wrap, plus a Today page.
- Add evidence-backed wraps and local CHANGELOG proposals. Every factual bullet cites `[signal:N]`, approval only appends `CHANGELOG.md` under a configured root, and the Wrap page can approve or reject a pending proposal.
- Add a deterministic standup of 5–8 bullets drawn from today's plan, the previous day's wrap, and high-priority todos, plus a Standup page that can copy them.
- Document the single `sb-core` process in the README architecture. The old two-server launch instructions are replaced by the prepared, not-yet-applied cutover.


## [2026-10-01]
- **15:11:27 UTC** · **Removed** Removed todo "Phase 2g smoke test task" `9`
- **15:11:17 UTC** · **Completed** Completed todo "Phase 2g smoke test task" `9`
- **15:11:13 UTC** · **Added** Added todo "Phase 2g smoke test task" `9`

## [2026-09-30]
- **19:17:50 UTC** · **Reviewed** it looks like the certificate used above is signed by an internal signer and there are some other hostnames that need to be used. I'll make a new PR to use them per-env. `Common AI - Agent Team`

