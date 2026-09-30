# Changelog

## Unreleased

### Changed

- Reconcile the working tree before the unified MCP rollout. Baseline before Step 1: todos 18 passed, JIRA 14 passed, web MCP client 5 passed, and `tsc --noEmit` clean. The core suite is not green; unfinished ritual tests stay out of the active set until their step.
