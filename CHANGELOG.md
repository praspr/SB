# Changelog

## Unreleased

### Changed

- Reconcile the working tree before the unified MCP rollout. Baseline before Step 1: todos 18 passed, JIRA 14 passed, web MCP client 5 passed, and `tsc --noEmit` clean. The core suite is not green; unfinished ritual tests stay out of the active set until their step.

### Added

- Scaffold `sb-core` on `127.0.0.1:8787` with a metadata-only SQLite schema, `system_status`, `/health`, and a `/status` page. Domain REST routes stay absent. Launchd plist is prepared; login cutover is documented and not applied.
- Mount the eight todo tools in-process on the same MCP, with a fresh SQLite connection per call, and point the Todos UI at that client. The standalone todos REST app and launchd plist are removed from the repo.
- Mount the four pull-only JIRA tools on the same MCP and point the JIRA page at that client. Health does not probe Atlassian. The standalone JIRA REST app and launchd plist are removed from the repo.
- Index `SKILL.md` files from allow-listed project, Cursor, Claude, and configured roots, and expose them as MCP tools, prompts, and resources plus a Skills page. Content is identified with SHA-256. Symlinks that leave a root are ignored.
- Add changelog, git, todo, and local JIRA signal adapters with `sync_adapters`, `sync_status`, and `search_signals`, and a Signals page that cites `[signal:N]`.
