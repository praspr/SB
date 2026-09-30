At start of a session, call `ledger_context(project=<detected from working_dir>)` to load recent context.

After each meaningful action, call `ledger_log(...)` to record it.

Include refs (`jira`, `pr`, `commit`, `file`, `webex`) whenever possible.

Do not attempt to update or delete — the ledger is append-only.
