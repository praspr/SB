# Platform Account Lookup

Resolve a **customer display name** to a **platform account id** (UUID), or the
reverse, before Postgres queries, replay, or other Config SaaS workflows that
require `platform_account_id`.

This workflow uses the bundled helper:

```bash
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name <substring>
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account <uuid-or-substring>
```

## When to use

- You have a customer name (e.g. `hdfc`) but need the platform account UUID for
  `run_postgres_query.sh` or
  [`replay-assessment-execution.md`](replay-assessment-execution.md).
- You have a partial or full platform account id and need the canonical account
  name and UUID.
- Do **not** guess `platform_account_id` — look it up first. Replay and
  Postgres filters keyed on the wrong id will silently miss rows.

## Commands

| Goal | Command |
| --- | --- |
| Name → account(s) | `bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name hdfc` |
| UUID → account name | `bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account 79a2cce0-d5d8-4ff9-a0e3-97221a73abd8` |
| Partial UUID | `bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account 79a2cce0` |
| Raw JSON | add `--json` |

Exactly one of `--name` / `--account` is required. Both fields are substring
searches against the scripts.cisco.com job API.

## Credentials (automatic)

The script needs `BDB_CLIENT_ID` and `BDB_CLIENT_SECRET` (OAuth client
credentials for scripts.cisco.com). Resolution order:

1. Existing shell environment
2. `$SKILL_DIR/.env`
3. Repo `.env` (if present)
4. Auto-fetch from dev `agent-secrets`, then write `$SKILL_DIR/.env` (created
   if missing, mode `600`)

Secret source (fixed for this workflow — always dev):

- Secret ID: `cx/usw2/dev01/configbp-ai/secrets/agent-secrets`
- Profile: `platform-dev-admin`
- Region: `us-west-2`

If AWS access fails, run `duo-sso` once and retry. Manual fetch details:
[`secrets-manager.md`](secrets-manager.md) → "Fetching `BDB_CLIENT_ID` /
`BDB_CLIENT_SECRET`".

Never commit `$SKILL_DIR/.env` or paste credential values into chat.

## API and response shape

- OAuth: `POST https://id.cisco.com/oauth2/default/v1/token` (client credentials)
- Job API: `POST https://scripts.cisco.com/api/v2/jobs/cisco_iq_account_query`
- Request body: `{ "input": { "account_search": "<name or empty>", "account_users": "<id or empty>" } }`

The HTTP response is JSON. The useful table is HTML embedded in
`data.variables.stdout` (not structured rows). Typical columns:

| Column | Notes |
| --- | --- |
| Account Name | Customer display name |
| Region | e.g. APJC, AMER |
| AccountID | Platform account UUID — use this as `platform_account_id` |
| Domain | Customer email domain |
| Date Created | Account creation date |
| Admin Emails | Treat as customer-sensitive |

### Extracting the platform account id

Prefer parsing the UUID from `data.variables.stdout` rather than hand-copying
from pretty-printed JSON. Example (does not print secrets):

```bash
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name hdfc 2>/dev/null \
  | python3 -c '
import json, re, sys
data = json.load(sys.stdin)
stdout = data.get("data", {}).get("variables", {}).get("stdout", "")
match = re.search(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    stdout,
    re.I,
)
print(match.group(0) if match else "no match")
'
```

## Privacy

- Treat account names, domains, admin emails, and platform account ids as
  **customer-sensitive**.
- Prefer summarizing lookup results in chat; do not dump full API JSON unless
  the user explicitly asks.

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `BDB credentials not set; fetching...` then failure | AWS SSO expired or wrong profile | `duo-sso`; confirm `platform-dev-admin` |
| `AccessDeniedException` on Secrets Manager | Used `cx-platform-*` master profile | Switch to `platform-dev-admin` |
| OAuth token request failed | Rotated BDB creds in SM but stale `.env` | Delete `BDB_*` lines from `$SKILL_DIR/.env` and re-run (auto-refetch) |
| Empty table / no UUID in stdout | Substring too narrow or wrong spelling | Broaden `--name` search; try `--account` if you have a partial id |
| Multiple rows returned | Substring matched several accounts | Disambiguate with the user before using an id in prod workflows |
