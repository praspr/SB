# Track JIRA Design

## Goal

Let a user paste a Cisco Atlassian issue URL or issue key on the JIRA page and
have that issue remain part of the second-brain JIRA mirror, including when it
is not returned by the assigned-issues JQL.

Tracking is local and pull-only. The feature never modifies Atlassian.

## User experience

The JIRA page adds a compact **Track JIRA** form above the filters:

- Accepted input: `CXP-123`, `CXPL-123`, or
  `https://cisco-cxe.atlassian.net/browse/CXP-123`.
- Submitting validates and normalizes the value to an uppercase issue key.
- The app fetches that issue read-only, writes its canonical markdown mirror,
  updates the local JIRA index, and refreshes the page queries.
- Success identifies the tracked key. Invalid input, authentication failure,
  permission denial, and missing issue errors are shown beside the form.
- A tracked issue stays tracked until explicitly removed. Removing a key from
  the tracked set is supported by the MCP domain, but a removal control is not
  part of this first UI change.

## Persistence

Tracked keys are stored in
`/Users/praspr/Documents/code_home/ciq/docs/jira/tracked.json`. The file has a
small versioned shape:

```json
{"version": 1, "keys": ["CXP-123"]}
```

Writes are atomic and keys are unique and sorted. The file contains no
credentials. Ticket content continues to live only in
`docs/jira/tickets/{KEY}.md`.

## Backend flow

The unified MCP exposes:

- `track_jira(issue)` — parse the key, persist it, fetch the issue through
  `GET /rest/api/3/issue/{key}`, write the markdown mirror, and regenerate the
  README index.
- `untrack_jira(key)` — remove only the key from tracking metadata. It does not
  delete the mirrored ticket file.
- `jira_status()` adds `tracked_count`.

The existing `sync_jira()` first fetches assigned issues through enhanced JQL,
then fetches every tracked key individually. Results are merged by key before
the existing atomic file sync. A failure for one tracked key is reported but
does not discard successfully fetched assigned issues or other tracked issues.

Issue keys are restricted to `[A-Z][A-Z0-9]*-\d+`. URLs are accepted only when
their host matches the configured Atlassian site and their path is exactly a
`/browse/{KEY}` issue path.

## Security boundaries

- Atlassian access remains GET-only.
- The existing API token remains in the keychain or environment; it is never
  returned to the browser or written to disk.
- No credential or certificate is added to source control.
- Tracking metadata contains issue keys only.
- The configured Atlassian TLS verification remains enabled.

## Testing

Backend tests cover key and URL parsing, foreign-host rejection, GET-only issue
fetching, atomic tracked-key persistence, idempotent tracking, merge behavior
during normal sync, and partial tracked-key failures.

Web tests cover the `track_jira` MCP request, query invalidation, successful
feedback, invalid input feedback, and disabled/loading form states.

Regression verification runs the JIRA and core suites, web tests, TypeScript
checking, and the production web build.
