# Clean Landing and Todos Design

## Goal

Make the landing page a quiet daily decision surface and make the Todos page
more useful and visually structured without changing backend behavior.

## Landing page

- Show one compact daily header.
- Show only three primary areas: needs attention, top todos, and upcoming
  meetings.
- Do not duplicate tasks, meetings, ledger deltas, usage, or status analytics.
- Keep the assistant available through a compact expandable panel rather than a
  permanently tall third column.
- Link to dedicated pages for complete lists and reports.

## Todos page

- Use the existing global page header without repeating the title and subtitle.
- Keep quick add prominent.
- Add a compact summary for overdue, due today, open, and completed tasks.
- Group visible tasks into Today, Upcoming, and No date; completed tasks use a
  Completed group.
- Add search and sorting alongside existing status and priority filters.
- Preserve JIRA import, completion, goals, recurrence, and source metadata.

## Constraints

- Frontend-only layout and presentation change.
- Preserve all MCP calls and mutation behavior.
- No new dependencies.
- Responsive at desktop and narrow widths.
- Existing dark visual language remains, with fewer bordered containers and
  stronger text hierarchy.

## Verification

- Unit tests cover landing content hierarchy and todo grouping/filter behavior.
- Existing web tests, TypeScript checking, and production build remain green.
