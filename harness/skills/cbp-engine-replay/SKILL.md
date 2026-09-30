---
name: cbp-engine-replay
description: >-
  Use when replaying a cbp-engine assessment execution: derive assessment_id,
  insert a pending execution row into Aurora, and explicitly publish via the
  native cbp-engine producer Kafka path (send_assessment_execution). Trigger on:
  replay an assessment, re-trigger a stuck or missing execution, manually publish
  to Kafka for cbp-engine, debug PENDING executions that were never picked up.
triggers:
  - user
  - model
---

# cbp-engine Replay Skill

Scoped to **assessment-unified-engine** (`cbp-engine`). Covers the full ordered
sequence: Aurora read-only derivation → execution row insert → **explicit Kafka
publish** via `send_assessment_execution`.

The Kafka publish step is **mandatory** — inserting the execution row without
publishing means the worker never picks it up. Both steps must complete.

---

## Layout

### Scripts

| Script | Use |
| --- | --- |
| `scripts/run_postgres_query.sh` | Aurora/Postgres queries and mutations via Kubernetes debug pod. Handles auth retry, credential caching, Excel output. |
| `scripts/postgres_query_cache.sh` | Credential cache helper — sourced automatically by `run_postgres_query.sh` |

### Docs

| Doc | Use |
| --- | --- |
| `docs/replay-assessment-execution.md` | Full 9-step ordered replay runbook — input validation → assessment derivation → execution row insert → Kafka publish → post-publish verification |

---

## Resolve `SKILL_DIR`

```bash
SKILL_DIR="/Users/praspr/.claude/skills/cbp-engine-replay"
```

Invoke the Postgres helper always via `$SKILL_DIR/scripts/`:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" dev "select 1;"
bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 "select 1;"
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 "select 1;"
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 --excel "select * from t limit 10;"
```

Do not invoke `run_postgres_query.sh` directly from the repo or from a relative
path. Always use `$SKILL_DIR/scripts/`.

---

## Script Defaults

`run_postgres_query.sh` is pre-configured for the `cbp-engine` Aurora path:

| Setting | Default |
| --- | --- |
| Kubernetes namespace | `sre-baseapps` |
| Secret namespace | `cxp-query-service` |
| Secret name | `cxp-baqs-creds` |
| Dev context | `cx-dev-usw2` |

Override any of these per-call via env vars: `KUBE_NAMESPACE`, `SECRET_NAMESPACE`,
`SECRET_NAME`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`POSTGRES_POD`, `KUBE_CONTEXT`.

---

## Core Rules

- **Never guess** `platform_account_id` or `management_system_id` — stop and ask if unknown.
- **Read-only derivation always first** — run SELECT queries before any INSERT.
- **Prod requires explicit confirmation** before any INSERT or Kafka publish.
- **`payload_json` must be populated** — the DB Queue worker marks the execution
  FAILED immediately if `payload_json` is NULL ("Claimed execution has no payload").
- **Both DB INSERT and Kafka publish are mandatory** — step 7 and step 9 must
  both complete. Do not treat the INSERT alone as a complete replay.
- **`duo-sso` is reactive only** — run it when an AWS/kubectl call fails with an
  auth error; never run it proactively before starting the workflow.

---

## `duo-sso` Agent Behavior

`duo-sso` is the AWS SSO credential refresh for this machine. It is
non-interactive: triggers a Duo push and exits in ~10–30 seconds.

- Run **reactively** when kubectl or AWS calls fail with auth/credential errors.
- Do **not** pre-run before starting the workflow.
- Two warnings about missing roles are normal and non-fatal:
  ```
  ✗ Account '...' or Role: 'AWS-CXP-InfraCore-...' not found
  ```
  As long as `cx-platform-*` and `platform-*-admin` profiles show `✓ AWS Credentials saved`,
  auth succeeded.

---

## Workflow — Quick Reference

Follow `docs/replay-assessment-execution.md` for the full ordered runbook.
Summary:

| Step | Action | Tool |
| --- | --- | --- |
| 1 | Validate `PLATFORM_ACCOUNT_ID` + `MANAGEMENT_SYSTEM_ID` are set | local shell |
| 2 | Read-only: derive existing `assessment_id` | `run_postgres_query.sh` SELECT |
| 3 | Read-only: category count check | `run_postgres_query.sh` SELECT |
| 4 | Repair missing category rows if needed | `run_postgres_query.sh` INSERT WHERE NOT EXISTS |
| 5 | Confirm exactly one `ASSESSMENT_ID` | — |
| 6 | Generate `EXECUTION_ID` | `date -u` |
| 7 | Build `PAYLOAD_JSON` and insert execution row | `run_postgres_query.sh` INSERT |
| 8 | Verify inserted row | `run_postgres_query.sh` SELECT |
| **9** | **Resolve producer pod + publish via `send_assessment_execution`** | `kubectl exec` |
| 10 | Post-publish verification | `run_postgres_query.sh` SELECT |

---

## Current UDM Table Versions

Use these in `PAYLOAD_JSON` (step 7) and the Kafka publish payload (step 9).
Update when the data fabric team bumps table versions.

| Field | Table name |
| --- | --- |
| `udm_asset_table` | `udm_asset_1__0__10` |
| `udm_asset_telemetry_table` | `udm_asset_telemetry_1__0__9` |
| `udm_command_table` | `udm_device_command_1__0__7` |
| `udm_software_table` | `udm_software_1__0__7` |
| `udm_product_table` | `udm_product_1__0__6` |
| `udm_contract_coverage_table` | `udm_contract_coverage_1__0__11` |

---

## Environment / Context Matrix

| `env` arg | `region` arg | kubectl context |
| --- | --- | --- |
| `dev` | (omit) | `cx-dev-usw2` |
| `nprd` | `usw2` / `apse2` / `euc1` | `cx-nprd-<region>` |
| `prod` | `usw2` / `apse2` / `euc1` | `cx-prd-<region>` |

Producer pod namespace for `kubectl exec`: `assessments-configuration`

---

## Updating This Skill

- `scripts/run_postgres_query.sh` — update when Kubernetes namespace, secret
  names, or context defaults change for `cbp-engine`.
- `docs/replay-assessment-execution.md` — update when the execution table schema,
  `payload_json` structure, or UDM table versions change. Keep all
  `$SKILL_DIR/scripts/run_postgres_query.sh` path references (not `resources/`).
- UDM table version table above — keep in sync with `docs/replay-assessment-execution.md`
  payload field reference.

Base directory for this skill: file:///Users/praspr/.claude/skills/cbp-engine-replay
