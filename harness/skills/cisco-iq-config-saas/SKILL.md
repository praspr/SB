---
name: cisco-iq-config-saas
description: 'Use when working on Cisco IQ Config SaaS operations across configbp-ai, cbp-engine, or cxp-cbp-etl: AWS auth, kubectl contexts, APISIX tunnels, Aurora/Postgres queries, Iceberg/UDM queries, lifecycle ETL references, Kafka topics, Secrets Manager paths, customer configuration assessment debugging, Splunk APM trace analysis, configbp-ai LangSmith agent trace/routing debugging, or fetching cxdocs.cisco.com / CX Platform Docs / Cisco IQ documentation / IQ docs / cxdocs pages as Markdown via cxdocs-cli.'
triggers:
  - user
  - model
---

# Cisco IQ Config SaaS

This skill is the self-contained operational guide for Cisco IQ Configuration
SaaS. It covers the `configbp-ai`, `cbp-engine`, and `cxp-cbp-etl` workflows.

## Layout

The skill bundles **scripts** (executables) and **docs** (runbooks and reference).

Run helpers from [`scripts/`](scripts/). Read runbooks from [`docs/`](docs/).

### Scripts

| Script | Use |
| --- | --- |
| `scripts/setup_kube_context.sh` | Lightweight kubeconfig alias bootstrap (no sudo, no port-forward) for `cx-<env>-<region>` contexts |
| `scripts/run_postgres_query.sh` | Aurora/Postgres ad hoc queries through Kubernetes debug pods |
| `scripts/postgres_query_cache.sh` | Credential cache helper used by `run_postgres_query.sh` |
| `scripts/local_apisix_setup.sh` | Local APISIX port-forward (sudo + foreground) — for ad hoc APISIX/Trino debugging, not needed for Iceberg/UDM queries |
| `scripts/run_iceberg_query.sh` | Iceberg/UDM queries via Athena directly against the Glue Data Catalog (no APISIX, no sudo) |
| `scripts/query_cisco_iq_account.sh` | Resolve customer name ↔ platform account id via scripts.cisco.com |
| `scripts/_iceberg_query.py` | Python helper used by `run_iceberg_query.sh` |
| `scripts/fetch_langsmith_trace.py` | Fetch a public LangSmith trace share URL — overview/messages/tokens/tools/raw |
| `scripts/search_langsmith_runs.py` | Search authenticated configbp-ai (`ciq-agents-*`) LangSmith traces by thread/account/user/run id |
| `scripts/cxdocs.sh` | `fetch`/`search` cxdocs.cisco.com / CX Platform Docs / Cisco IQ documentation / IQ docs pages as Markdown via `cxdocs-cli` (auto-installs the tool; agent may run `cxdocs-cli login` itself first) |

### Reference docs

| Doc | Use |
| --- | --- |
| `docs/config-saas-reference.md` | Cross-repo operational reference (services, namespaces, Kafka topics, pipeline diagram) |
| `docs/table-registry.md` | Current Config SaaS table registry for SQL construction |
| `docs/postgres-query-recipes.md` | `run_postgres_query.sh` flags (`--excel`, etc.) and reusable SQL templates |
| `docs/baqs-resolvers.md` | BAQS resolver architecture, multi-management-system model, SQL optimization patterns, 4 resolver deep-dives, 8-query validation suite |
| `docs/secrets-manager.md` | AWS Secrets Manager recipes, per-region secret IDs, profile-vs-account gotcha |
| `docs/slic-artifacts.md` | Read-only download of current dev/nprd/prod USW2 SLIC rules/IC artifacts, `local_store.json` and `ic_bom.json` (`scripts/download_slic_artifacts.sh`) |
| `docs/apisix-trino-internals.md` | APISIX → Trino principal mapping, macOS `.local` DNS pin — for ad hoc APISIX/Trino debugging (not used by `run_iceberg_query.sh` anymore) |
| `docs/splunk-observability.md` | Fetch an APM trace's span waterfall (SignalFx GraphQL API) by trace ID — for finding the real bottleneck behind a slow GraphQL/API call or Agent span |
| `docs/langsmith-trace.md` | Analyze configbp-ai agent LangSmith traces — routing verdict, tool/LLM calls, token usage, Jira feedback-ticket root cause — or fetch a public LangSmith share URL |
| `docs/debugging-no-findings.md` | "Customer has no findings" runbook with full UDM eligibility SQL |
| `docs/platform-account-lookup.md` | Customer name ↔ platform account id via `query_cisco_iq_account.sh` |
| `docs/replay-assessment-execution.md` | Ordered replay runbook using `run_postgres_query.sh` for Postgres steps and native cbp-engine producer code for publish |
| `docs/cxdocs-cli.md` | cxdocs-cli setup, `login` (agent may run bare/foreground first, else user-run), fetch modes (`--full`/`--body`/`--nav`), session lifecycle — for cxdocs.cisco.com / CX Platform Docs / Cisco IQ documentation / IQ docs lookups |

## Resolve `SKILL_DIR`

Before running a bundled helper, resolve the directory containing this
`SKILL.md` and call scripts with `bash`:

```bash
SKILL_DIR="/absolute/path/to/.claude/skills/cisco-iq-config-saas"
bash "$SKILL_DIR/scripts/setup_kube_context.sh" nprd usw2
bash "$SKILL_DIR/scripts/run_postgres_query.sh" dev "select 1;"
bash "$SKILL_DIR/scripts/run_iceberg_query.sh" nprd usw2 "SELECT 1"
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name hdfc
```

If the runtime does not provide the skill path, use the known project install:

```bash
SKILL_DIR="/Users/aabhish2/Documents/configbp-ai/.claude/skills/cisco-iq-config-saas"
```

Do not `chmod`, copy, or rewrite bundled scripts before execution. The
executable bit is not required when invoking with `bash`.

## Core Rules

- Use bundled helpers first. Do not run `./scripts/run_postgres_query.sh`,
  `./scripts/local_apisix_setup.sh`, or `./scripts/run_iceberg_query.sh`
  from whichever repo happens to be open.
- If AWS, kubectl, Secrets Manager, or Athena access fails due to auth, run
  `duo-sso` once and retry the original command. See
  [`duo-sso` agent behavior](#duo-sso-agent-behavior) below.
- **Never run `local_apisix_setup.sh` yourself.** It needs `sudo` (ports
  80/443, `/etc/hosts`) and runs in the foreground, so the agent cannot
  start it. Iceberg/UDM queries do **not** need it — `run_iceberg_query.sh`
  goes through Athena directly. Only reach for `local_apisix_setup.sh` for
  ad hoc APISIX/Trino debugging outside that path, and even then give the
  user the exact command to run in their own terminal. See
  [APISIX agent behavior](#apisix-agent-behavior) below.
- For SQL, open [`docs/table-registry.md`](docs/table-registry.md)
  before choosing table names.
- For cross-service context, open
  [`docs/config-saas-reference.md`](docs/config-saas-reference.md).
- Production is read-only for ad hoc data access. Run `SELECT` only and use
  `LIMIT` for exploratory queries.
- Replay is the documented exception: do read-only derivation first, get
  explicit confirmation before mutating prod, then follow the replay runbook
  exactly.
- Treat customer rows, command outputs, findings, platform account IDs, and
  secret payloads as sensitive. Prefer counts, schemas, and redacted summaries.
- Confirm with the user before any dev/nprd Secrets Manager write. Do not
  attempt prod writes.
- Never paste service credentials, base64 credential values, secret JSON, private
  keys, or certificate material into chat or skill files.
- `BDB_CLIENT_ID` / `BDB_CLIENT_SECRET` for `query_cisco_iq_account.sh` are
  auto-managed in `$SKILL_DIR/.env` (gitignored). See
  [`docs/platform-account-lookup.md`](docs/platform-account-lookup.md).
- If `cxdocs.sh` reports no valid session, try `cxdocs-cli login`
  yourself — bare command, foreground, no absolute path, no
  backgrounding. Give it ~45-60s; only fall back to asking the user to run
  it themselves if it's still hanging. See
  [cxdocs-cli agent behavior](#cxdocs-cli-agent-behavior) below.

## Environment Matrix

| Env | Region args | Contexts |
| --- | --- | --- |
| `dev` | single-region `usw2` | `cx-dev-usw2` |
| `nprd` | `usw2`, `apse2`, `euc1` | `cx-nprd-usw2`, `cx-nprd-apse2`, `cx-nprd-euc1` |
| `prod` | `usw2`, `apse2`, `euc1` | `cx-prd-usw2`, `cx-prd-apse2`, `cx-prd-euc1` |

Primary app namespace:

```text
assessments-configuration
```

## `duo-sso` agent behavior

`duo-sso` is the AWS/SSO credential refresh command for this machine. It is
**non-interactive**: it triggers a Duo push to the user's pre-registered
device and exits in ~10–30 seconds with an exit code. It does not block on
terminal input.

Agent rules:

- Run `duo-sso` **reactively** when an AWS, kubectl, or Secrets Manager call
  fails with an auth/credential error. The bundled `run_postgres_query.sh`
  and `run_iceberg_query.sh` already auto-refresh on auth failure, so you
  typically do not need to pre-run it before those helpers.
- Do **not** pre-run `duo-sso` proactively at the start of every workflow.
  Only run it after a failure or when access is clearly stale.
- The agent **MUST NOT** ask the user "ready?" / "should I refresh auth?"
  before running it. Just run it via a normal shell call.
- Do not prefix with `!`. From a shell tool, call `duo-sso` plainly.
- Recommended `block_until_ms` ≈ 60000 to absorb the Duo push round-trip.
- Two warnings are normal and not fatal:

  ```text
  ✗ Account '905418369215' or Role: 'AWS-CXP-InfraCore-nprd-Admin' not found
  ✗ Account '905418369215' or Role: 'AWS-CXP-InfraCore-prod-Admin' not found
  ```

  As long as `cxp-aws-readonly`, `cx-platform-dev-admin`,
  `cx-platform-nprd-admin`, and `cx-platform-prod-readonly` show
  `✓ AWS Credentials saved`, auth succeeded for the profiles this workflow
  needs.

## APISIX agent behavior

`local_apisix_setup.sh` starts a local APISIX port-forward for ad hoc
APISIX/Trino debugging. Unlike `duo-sso`, the agent **must not run it**:
it requires `sudo` (binds ports 80/443 and edits `/etc/hosts`) and then
blocks in the foreground holding the tunnel open. An agent shell call
cannot supply the sudo password and would hang.

Agent rules:

- When a workflow needs the APISIX tunnel, **stop and ask the user to run
  the exact command** in a separate terminal, then wait for them to confirm
  the port-forward is up before continuing:

  ```bash
  bash "$SKILL_DIR/scripts/local_apisix_setup.sh" <env> [<region>]
  ```

  Substitute the real `env` / `region` for the target and, where the path
  is known, expand `$SKILL_DIR` to the absolute path so the user can
  copy-paste without editing.
- Do **not** try to run it in the background, with `sudo -n`, or by piping
  a password — none of those work and they leave the user with a stuck
  shell.
- The agent may still run the no-sudo `setup_kube_context.sh` itself to
  bootstrap the kubeconfig alias. Only the port-forward step is user-run.

## cxdocs-cli agent behavior

`cxdocs-cli` fetches cxdocs.cisco.com (CX Platform Docs / Cisco IQ
documentation / IQ docs) pages as Markdown.

- `fetch`/`search` — safe for the agent to run directly via `scripts/cxdocs.sh`.
  Both are stateless-per-call reads that reuse the stored session cookie;
  the wrapper also auto-installs `cxdocs-cli` via `uv tool install` if it's
  missing.
- `login` — opens a real Chrome window for Cisco Duo SSO. **The agent may
  attempt this itself first**, run bare and in the foreground:

  ```bash
  cxdocs-cli login
  ```

  Confirmed (2026-08-12): when run this way — bare command, no absolute
  path, not backgrounded with `&` — it reliably completes on its own within
  seconds, auto-filling the SSO email and capturing the session, with no
  visible manual click needed. Backgrounding it (`cxdocs-cli login &`,
  redirected to a log file) or invoking it by full path did **not**
  complete the same way in testing — always run it bare and in the
  foreground.

Agent rules:

- If `cxdocs.sh fetch`/`search` fails because no valid session exists
  (never logged in, or the ~8h session expired), run `cxdocs-cli login`
  bare/foreground yourself first, then retry the original `fetch`/`search`
  call.
- Give it a bounded wait (~45–60s). If it's still hanging with no
  "Session captured successfully!" line, it's likely hit a case needing a
  fresh, visible Duo push tap that this run can't get you — stop and ask
  the user to run `cxdocs-cli login` themselves in their own terminal, then
  retry once they confirm it succeeded.
- Do not background it or invoke it by absolute path — both were observed
  to hang instead of completing.

## Kubernetes Context Naming (Team-Wide)

The bundled helpers in this skill that talk to Kubernetes
(`run_postgres_query.sh`, `local_apisix_setup.sh`) select a context using a
single team-wide alias convention.

| `env` arg | `region` arg | Expected kubeconfig context |
| --- | --- | --- |
| `dev` | (implicit `usw2`) | `cx-dev-usw2` |
| `nprd` | `usw2` / `apse2` / `euc1` | `cx-nprd-<region>` |
| `prod` | `usw2` / `apse2` / `euc1` | `cx-prd-<region>` |

Note `prod` resolves to the alias prefix **`cx-prd-`** (not `cx-prod-`).
These aliases are not personal — they are the canonical names this team
standardizes on so that scripts, docs, and on-disk cache files are
portable across laptops.

### How the aliases get there

This skill owns alias bootstrap as its own concern via a dedicated helper:

```bash
bash "$SKILL_DIR/scripts/setup_kube_context.sh" dev
bash "$SKILL_DIR/scripts/setup_kube_context.sh" nprd usw2
bash "$SKILL_DIR/scripts/setup_kube_context.sh" prod apse2

bash "$SKILL_DIR/scripts/setup_kube_context.sh" --all   # all targets
```

`setup_kube_context.sh` is intentionally lightweight — it **only** writes
the canonical kubeconfig context alias via
`aws eks update-kubeconfig --alias cx-<env>-<region> ...`. It does not
require sudo, does not start a port-forward, does not touch `/etc/hosts`,
and exits immediately on success. If the alias already reaches the
cluster, it is a no-op. If the AWS session is stale, it triggers
`duo-sso` automatically; otherwise it skips it.

Use this for **any** workflow that needs kubectl access by alias —
Postgres queries via `run_postgres_query.sh`, status checks,
`kubectl get pods`, etc.

`local_apisix_setup.sh` does the same alias bootstrap as a side effect
**plus** starts a foreground sudo port-forward and adds an `/etc/hosts`
entry for the APISIX gateway. Use it for ad hoc APISIX/Trino debugging.

After running `setup_kube_context.sh` once per target, every
`run_postgres_query.sh <env> [<region>]` invocation works without
further configuration. Re-running the helper later is safe and cheap.

### If your kubeconfig already uses different context names

If your kubeconfig context for the same EKS cluster is something other
than `cx-<env>-<region>` (e.g. a raw EKS ARN, a Cisco SRE-issued name,
or an alias set up by another tool), you have two options. Prefer (1)
for long-term portability:

1. **Re-alias once** (recommended) — adopt the team convention so this
   skill, repo scripts, and teammates all key on the same names. The
   easiest path is the bundled helper, which already knows the right
   cluster name, AWS profile, role ARN, and EKS region per target:

   ```bash
   bash "$SKILL_DIR/scripts/setup_kube_context.sh" <env> [<region>]
   ```

   If you must do it by hand:

   ```bash
   aws --profile <your-eks-profile> eks update-kubeconfig \
     --region <aws-region> \
     --name <eks-cluster-name> \
     --alias cx-<env>-<region>
   ```

2. **Per-call override** — set `KUBE_CONTEXT` to your local context name
   for a single invocation. The helpers respect it and skip the alias
   lookup entirely:

   ```bash
   KUBE_CONTEXT=arn:aws:eks:us-west-2:123456789012:cluster/cbp-prod \
     bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 "select 1;"
   ```

### Cache filenames are keyed on the resolved context

`run_postgres_query.sh` writes per-target credential caches under
`$SKILL_DIR/.cache/postgres/<context>.env` (one file per env+region, keyed
by the resolved kubeconfig context).

- The on-disk filenames will literally contain `cx-prd-usw2.env`,
  `nprd.env`, etc. on a standard setup — that is expected, not a bug.
- If you used a `KUBE_CONTEXT` override or a non-standard alias, your
  Postgres cache file will be named after **your** context. That is
  harmless for you, but the file is not shareable. `.cache/postgres` is
  local-only, gitignored, contains credentials, and must never be
  committed or pasted into chat.

### Agent rule

When an agent is asked to query a target from this skill, it should:

1. Pass `env` (and `region` where required) — never hardcode a context
   string into commands.
2. Only set `KUBE_CONTEXT=…` when the user explicitly says their
   kubeconfig uses a non-standard alias.
3. If a helper fails with a "context not found" or "no such context"
   error, run `setup_kube_context.sh <env> [<region>]` once and retry —
   do not guess at the user's local context name and do not start
   `local_apisix_setup.sh` (with its sudo port-forward) just to bootstrap
   an alias.

## Common Workflows

### Aurora/Postgres Investigation

1. Read [`docs/table-registry.md`](docs/table-registry.md) for
   logical → physical table names.
2. Use the bundled query wrapper:

   ```bash
   bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 "SELECT count(*) FROM assessmentsapp__table__unified_config_assmt_finding_pg;"
   ```

3. Summarize results without exposing raw customer-sensitive rows unless the
   user explicitly asks.

For helper flags (`--excel`, `EXCEL_OUTPUT`, `OUTPUT_DIR`) and reusable
SQL templates such as "latest execution IDs per `platformAccountId`", see
[`docs/postgres-query-recipes.md`](docs/postgres-query-recipes.md).

### Customer / platform account lookup

Use this **before** Postgres or replay when you only have a customer name (or
need to confirm a platform account id). Full runbook:
[`docs/platform-account-lookup.md`](docs/platform-account-lookup.md).

```bash
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --name hdfc
bash "$SKILL_DIR/scripts/query_cisco_iq_account.sh" --account 74833d3a-1d15-4060-ad4b-080fea8ce444
```

Do not guess `platform_account_id`.

### Local APISIX Access

For ad hoc APISIX/Trino debugging (not needed for Iceberg/UDM queries —
see below). User-run, not agent-run — the script needs `sudo` for ports
80/443 and stays in the foreground (see
[APISIX agent behavior](#apisix-agent-behavior)). Ask the user to run the
matching command in a separate terminal and keep that terminal open:

```bash
bash "$SKILL_DIR/scripts/local_apisix_setup.sh" dev
bash "$SKILL_DIR/scripts/local_apisix_setup.sh" nprd usw2
bash "$SKILL_DIR/scripts/local_apisix_setup.sh" prod apse2
```

### Iceberg/UDM Investigation

`run_iceberg_query.sh` queries UDM Iceberg tables via Amazon Athena
directly against the Glue Data Catalog — no APISIX tunnel, no sudo, no
Trino credential. Auth is the same `platform-<env>-admin` SSO profile
used elsewhere in this skill, refreshed automatically via `duo-sso` on
an expired session.

1. Read [`docs/table-registry.md`](docs/table-registry.md) for UDM table
   names.
2. Run:

   ```bash
   bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod usw2 "SHOW TABLES"
   bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod usw2 \
     "SELECT count(*) FROM assetsudm__table__udm_asset"
   ```

   `dev` implies `usw2`; `nprd`/`prod` require a region. Output defaults
   to the Data Fabric team's own
   `cx-<region>-<env>01-datafabric-s3-datalakehouse` bucket — override
   with `--output-s3` only if that bucket is ever unavailable for a
   target.

### AWS Secrets Manager Operations

For reading or modifying `agent-secrets`,
`assessments-configuration-secrets`, or `cbp-lifecycle-etl-secrets`,
follow [`docs/secrets-manager.md`](docs/secrets-manager.md).
It contains the profile-vs-account gotcha
(use `platform-*-admin` assumed profiles, not `cx-platform-*`),
per-region secret ID tables, and the canonical read-merge-put,
remove, whitespace-strip, and rollback recipes.

- Confirm with the user before any dev/nprd write.
- Do not perform prod writes from this skill.
- Do not print full secret payloads into chat.

### Customer Has No Findings

Follow the full end-to-end runbook in
[`docs/debugging-no-findings.md`](docs/debugging-no-findings.md).
The runbook walks Aurora → UDM Iceberg eligibility → cbp-engine
worker/cache, with the SLIC-equivalent UDM eligibility SQL inline.

High-level path:

1. Check Aurora assessment / execution / tracking rows with
   `run_postgres_query.sh`.
2. If no rows exist, inspect ETL/connector notification status from
   `cxp-cbp-etl` references and cbp-engine producer logs.
3. If executions exist with zero violations, check eligible UDM device data
   with `run_iceberg_query.sh` using the full SLIC eligibility query.
4. If eligible devices exist, inspect cbp-engine worker status and SLIC results.
5. If findings exist but answers are stale, inspect configbp-ai MCP/agent
   cache and expert insights paths.

### Replay Assessment Execution

Follow
[`docs/replay-assessment-execution.md`](docs/replay-assessment-execution.md)
for the canonical replay sequence.

High-level path:

1. Collect explicit `env`, `region`, `platform_account_id`, and
   `management_system_id`.
2. Use `run_postgres_query.sh` for all read-only derivation queries.
3. Derive `assessment_id` from
   `assessmentsapp__table__unified_assessments_pg`; create missing assessment rows only
   if required by the runbook.
4. Generate one `execution_id`, build the `payload` JSON (UDM table names +
   IDs), and insert one pending row into
   `assessmentsapp__table__unified_assessments_execution_pg` with
   `engine_status = 'PENDING'`. This insert **is** the trigger — cbp-engine's
   worker is spawned by KEDA's PostgreSQL scaler polling that column, not a
   Kafka publish.
5. Re-run verification queries; optionally watch `engine_status` flip to
   `INPROGRESS`/`COMPLETED` as the worker claims the row. **Gotcha**
   (verified live): the worker ScaledJob's `activationTargetQueryValue` is
   `1` in every env — KEDA only scales from zero once the `PENDING`-row
   count exceeds that (≥ 2), so a lone replay insert into an empty queue
   can sit at `PENDING` with no worker spawned. See
   [`docs/replay-assessment-execution.md`](docs/replay-assessment-execution.md)
   → "Watch the Claim" for the check and workaround.

Side effects:

- may create missing assessment rows for `Architecture & Configuration`
  and/or `Security`
- inserts one execution row (this is the only trigger needed)

Prod safety expectations:

- do read-only verification first
- get explicit confirmation before any prod mutation
- do not paste secrets, service credentials, or raw sensitive outputs into chat

### cxdocs.cisco.com / CX Platform Docs / Cisco IQ documentation / IQ docs lookup

Fetch a `cxdocs.cisco.com` page as Markdown. Full runbook:
[`docs/cxdocs-cli.md`](docs/cxdocs-cli.md).

```bash
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/ --body
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/ --nav
```

**Don't have the exact URL?** Search first:

```bash
bash "$SKILL_DIR/scripts/cxdocs.sh" search "table indexing"
```

Prints `Title -- URL` per match; feed a result's URL into `cxdocs.sh fetch`.

If either script reports no valid session, try `cxdocs-cli login` yourself
(bare command, foreground, no absolute path); only ask the user to run it
themselves if it hangs — see
[cxdocs-cli agent behavior](#cxdocs-cli-agent-behavior).

## Service Map

| Service | Operational focus |
| --- | --- |
| `configbp-ai` | User-facing agent responses, MCP query tools, Expert Insights, A2A gateway |
| `cbp-engine` | Notification producer, SLIC worker, IC/BOM packager, finding persistence |
| `cxp-cbp-etl` | Lifecycle definitions, Data Fabric tables, ETL instances, S3 connector, message topics |

## Updating This Skill

Update files under `scripts/` when helper behavior changes. Update files under
`docs/` when environment names, secret path conventions, table names, Kafka
topics, pipeline flow, or per-target identifiers change.

Specifically:

- `scripts/setup_kube_context.sh` — when EKS cluster names, regions, AWS
  profile names, or workload-account role ARNs change for any target.
  Keep the per-target mapping in lockstep with the
  `configure_environment` block in `scripts/local_apisix_setup.sh`.
- `docs/table-registry.md` — when `TRINO_TABLE_*` values change or UDM table
  versions are bumped by the data fabric team.
- `docs/baqs-resolvers.md` — when any of the four core resolvers
  (`assessmentExecutions`, `ruleEvaluations`, `findings`, `findingsCount`)
  change their SQL approach, dedup key, CTE structure, or pagination
  strategy. Also update when new count-discrepancy root causes are
  identified (e.g., new stale-exec_track patterns) or when the
  8-query validation suite is extended with new checks.
- `docs/secrets-manager.md` — when secret IDs, workload account numbers, or
  AWS profile names change. Also update when a new secret family
  (alongside `agent-secrets`,
  `assessments-configuration-secrets`,
  `cbp-lifecycle-etl-secrets`) is introduced.
- `docs/apisix-trino-internals.md` — when the APISIX credential → principal
  mapping changes (credential rotation, consumer rebuild), for ad hoc
  APISIX/Trino debugging.
- `scripts/run_iceberg_query.sh` / `scripts/_iceberg_query.py` — when Glue
  database naming, the `platform-<env>-admin` profile mapping, or the
  Data Fabric output bucket (`cx-<region>-<env>01-datafabric-s3-datalakehouse`)
  changes.
- `docs/debugging-no-findings.md` — when the cbp-engine worker eligibility
  rules (`software_type`, `cx_level`, command list,
  `command_status`/`command_response` filters) change.
- `docs/replay-assessment-execution.md` — when replay SQL ordering, required
  categories, producer-pod invocation, native publish call, or execution-row
  contract changes.
- `docs/platform-account-lookup.md` — when the account-query API, response
  shape, credential bootstrap, or `query_cisco_iq_account.sh` flags change.
- `docs/postgres-query-recipes.md` — when `run_postgres_query.sh` flags or
  default output behavior changes.
- `docs/config-saas-reference.md` — when Kafka topic names, cbp-engine role
  taxonomy, or the high-level pipeline shape changes.
- `scripts/cxdocs.sh` / `docs/cxdocs-cli.md` — when `cxdocs-cli`'s CLI
  flags, install source (`git+ssh://git@github.com/CXEPI/cxdocs-cli.git`),
  session/keyring behavior, or the search index location/shape
  (`/search/search_index.json`, an mkdocs-material convention) change
  upstream.

When updating from source repos, copy only executable/helper logic and
redacted metadata. Do not copy Helm values or env files wholesale because
they may contain credential material.
