# Context Actions and Scheduled Sync Design

## Goal

Close three workflow gaps: turn reviewed context into a todo, stop refreshing a
tracked JIRA, and keep JIRA/Webex mirrors fresh automatically.

## Create todo from context

JIRA rows, Webex attention rows, and meeting-note proposal rows expose a
**Create todo** action. The action opens the existing Add Todo dialog with
editable defaults rather than creating immediately.

The shared draft contains `title`, `description`, `external_source`,
`external_ref`, and optional `jira_ref`. Saving passes those fields to
`todo_add`. The existing `(external_source, external_ref)` upsert makes repeat
submissions idempotent.

Source mapping:

- JIRA: source `jira`, external ref and JIRA ref equal the issue key.
- Webex attention: source `webex`, external ref is the message ID, description
  includes the `[webex:<id>]` citation.
- Meeting proposal: source `webex-meeting`, external ref combines meeting ID
  and proposal ID, description retains the meeting reference.

## Untrack JIRA

`list_jira_tickets` adds a `tracked` boolean to each returned row. JIRA rows
with `tracked=true` show an **Untrack** action. Calling `untrack_jira` removes
the key from `tracked.json`, invalidates JIRA queries, and leaves the existing
markdown mirror in place.

## Scheduled pulls

The existing scheduler accepts `sync_jira` and `sync_webex` alongside rituals.
Settings exposes both names in the schedule selector.

On startup, the core database receives these enabled defaults only when no
schedule with the same name exists:

- `JIRA hourly sync`: `0 * * * *`
- `Webex 15-minute sync`: `*/15 * * * *`

The existing launchd scheduler evaluates them every five minutes. Sync errors
raise a scheduler error so `last_status` becomes `error`; successful pulls set
it to `ok`. Neither operation writes to Atlassian or Webex.

## Security and failure behavior

- JIRA and Webex remain pull-only.
- Existing Keychain credentials are used without exposing them.
- A failed sync keeps the previous local mirror.
- Creating a todo is the only new data mutation and affects local todo SQLite.
- No credentials or certificates are added to source.

## Verification

Tests cover draft prefill and idempotent fields, todo actions on all three
surfaces, tracked-row untracking, scheduler dispatch, default schedule seeding,
sync failure status, Settings options, and full backend/web regressions.
