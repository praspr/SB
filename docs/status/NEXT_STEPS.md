# sb — Next Steps

## Immediate: enable the JIRA loop

Without a JIRA token the adapter degrades gracefully (`probe: unavailable`),
and the rest of sb still works fine on changelog + git signals. To unlock
the full ranked plan against your 43 assigned tickets:

```bash
# 1. Get an Atlassian API token
#    cisco-cxe.atlassian.net → profile → Security → Create API token

# 2. Store it in Keychain (never in a file)
sb secret set jira.token
# paste the token when prompted (hidden input)

# 3. Verify
sb doctor
# jira row should now show: ✅ ok — Prasad P R (praspr@cisco.com)

# 4. First JIRA sync
sb sync --adapter jira
# ingests tickets as sb_signals + upserts them into TodoLocal tasks

# 5. First real ranked plan
sb plan
```

---

## Phase 2 queue

These are additive and independent — each unlocks one capability:

### Outlook JXA adapter (`adapters/outlook_jxa.py`)

- Reads mail + calendar via `osascript` against the Outlook `.sdef`
  dictionary (verified present on this machine, Outlook 16.112).
- Zero auth: uses the local Outlook profile.
- Emits calendar events as signals → `plan_day` becomes **meeting-aware**
  and generates time blocks around real meetings.
- Emits flagged/unread mail as signals for "unanswered ask" detection.

### Webex REST adapter (`adapters/webex.py`)

- Reads spaces, DMs, and @mentions via `webexapis.com` REST v1.
- Personal access tokens expire in 12 hours — a Webex Integration
  (OAuth refresh token) is required for daemon use.
- Emits mention signals → wrap detects unanswered pings older than 24h.

### launchd scheduler + notifications (`daemon/scheduler.py`)

- Adds a `Schedule` array to the existing plist:
  - 08:30 weekdays → notify "Ready to plan?" → runs `sync` in background
  - 17:30 weekdays → notify "Time to wrap" → runs `wrap --dry-run`
- Uses `osascript` for macOS notifications (title, subtitle, actions).

### `sb dash` — local web dashboard

- FastAPI + one dark-themed HTML page.
- Sections: Today's plan · Recent signals · Pending proposals · Sync status.
- Runs on the same `:8787` process (mounted under `/dash`).

### `sb init` onboarding wizard

- Interactive 10-minute setup for a teammate:
  - detects harnesses (Claude Code, OpenCode, Cursor, VS Code)
  - asks for identity + git_authors
  - offers to import goals from a template or scaffold from scratch
  - runs `sb install --all` at the end
  - final smoke test: `sb doctor` + `sb sync` + `sb plan`

### Semantic layer (deferred from Phase 0)

- Use `text-embedding-3-small` via claudegate (already available) to
  embed signals for near-duplicate detection and "have I seen this ask
  before?" queries.
- Only worth adding when the signal count crosses ~10k.

---

## Nice-to-haves (unranked)

- **`sb reflect`** — weekly pattern review (feeds on `search_signals`),
  mirrors the existing `reflect` skill's cadence.
- **`sb export --gap-report`** — Cisco-branded HTML gap analysis for
  weekly reviews.
- **`sb graphify`** — export `sb_signals` as a graph for the existing
  `graphify` skill.
- **Cursor rules refinement** — `sb.mdc` currently opts in on request;
  could become `alwaysApply` once trust is established.

---

## Known limitations

| Limitation | Workaround |
|------------|-----------|
| No timezone in signal timestamps beyond UTC | Fine for now; add per-domain TZ in Phase 2 |
| Ranker is pure keyword matching (no embeddings) | Deliberate — cheap, testable, transparent |
| `wrap` writes CHANGELOG entries as proposals, not files | Deliberate — user approves via `sb review` |
| No history search UI in TodoLocal GUI | GUI shows tasks fine; use `sb signals` for history |
| Outlook JXA needs Legacy Outlook | Detect + fall back to Graph device-code flow if needed |
| Webex tokens expire 12h | Phase 3 uses Webex OAuth Integration for refresh tokens |

---

## Sharing sb with a teammate

The repo is designed to be shareable:

1. Clone `sb/` to a machine.
2. `uv sync`
3. `cp profiles/{config,goals}.example.yaml ~/.config/sb/`
4. Edit those two files to point at their folders.
5. `sb secret set jira.token` (theirs).
6. `sb install --all`
7. `sb doctor` should be all green.

No personal data is in the repo. Config, goals, secrets, and cache
directories are all under `~/.config/sb/`, `~/.local/share/sb/`, and
Keychain — never in the repo tree.
