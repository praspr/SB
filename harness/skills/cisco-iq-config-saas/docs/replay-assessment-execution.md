# Replay Assessment Execution

This runbook replays a single assessment execution through the skill-native
Config SaaS operator path.

cbp-engine's worker trigger is KEDA's PostgreSQL scaler polling
`assessment_execution` for `engine_status = 'PENDING'` rows (see
`helm/templates/keda-scaledjob.yaml` /
`_helpers.tpl:kedaPendingExecutionQuery` in `assessment-unified-engine`) —
**not** a Kafka publish. Inserting one execution row with
`engine_status = 'PENDING'` and a populated `payload` column is itself the
trigger; KEDA spawns a worker job that claims the row directly from
Postgres. `cbp_engine.clients.platform_kafka.send_assessment_execution` still
exists in the codebase but is not called by the producer or worker anymore —
do not use it.

It uses the bundled Postgres helper for all Aurora writes and reads:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" <env> [region] "<sql>"
```

## Scope

This workflow intentionally performs controlled mutations:

1. create missing assessment rows if required
2. insert one pending execution row (this insert is the trigger)

Use read-only verification first. For prod, stop and get explicit confirmation
before any INSERT.

## Mandatory Inputs

- `env`
- `region` (`usw2`, `apse2`, `euc1` for `nprd`/`prod`; omit or use `usw2` for `dev`)
- `platform_account_id`
- `management_system_id`

Derived later:

- `assessment_id` from `assessmentsapp__table__unified_assessments_pg`
- `execution_id` generated for this replay

## Fail-Loud Rules

- Do not guess `platform_account_id`.
- Do not guess `management_system_id`.
- Stop if `assessment_id` cannot be uniquely derived after assessment-row repair.
- Stop if any verification query shows unexpected state.
- Do not print secrets, service credentials, or secret JSON into chat/logs.

## 1. Resolve `SKILL_DIR`

Run this resource from the installed skill bundle. Use the runtime-provided
skill directory and call bundled helpers relative to it:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" ...
```

Do not hardcode a workstation-specific absolute path in the runbook.

## 2. Validate Inputs Locally

Set explicit shell variables before running any SQL:

```bash
ENV="nprd"
REGION="usw2"
PLATFORM_ACCOUNT_ID="<platform-account-id>"
MANAGEMENT_SYSTEM_ID="<management-system-id>"
```

Fail immediately if either required ID is empty:

```bash
test -n "$PLATFORM_ACCOUNT_ID"
test -n "$MANAGEMENT_SYSTEM_ID"
```

For `dev`, the helper can be called without a region. For consistency, this
runbook keeps the region variable explicit and only includes it when required.

## 3. Read-Only Derivation: Existing Assessment Rows

Check existing assessment rows for the platform account before mutating:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
SELECT
  assessment_id,
  assessment_category,
  assessment_name,
  is_active,
  created_date,
  created_by,
  version,
  owner_name
FROM assessmentsapp__table__unified_assessments_pg
WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
ORDER BY assessment_id, assessment_category;
"
```

The target account must end up with exactly one logical assessment.
In this table, that means exactly one distinct `assessment_id` for the target
`platform_account_id`, and that single `assessment_id` must have two category
rows:

- `Architecture & Configuration`
- `Security`
or 
- `Config Assessment`
- `Security Assessment`

Expected good state:

| assessment_id | platform_account_id | assessment_category |
| --- | --- | --- |
| `asmt-123` | `<platform_account_id>` | `Architecture & Configuration` |
| `asmt-123` | `<platform_account_id>` | `Security` |

or

| assessment_id | platform_account_id | assessment_category |
| --- | --- | --- |
| `asmt-123` | `<platform_account_id>` | `Config Assessment` |
| `asmt-123` | `<platform_account_id>` | `Security Assessment` |

Invalid states that must stop the replay:

- only one category row exists
- both categories exist but under different `assessment_id` values
- zero assessment rows exist and you still cannot repair to one unique
  `assessment_id`

## 4. Read-Only Category Check

Use an explicit grouped check before any insert:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
SELECT
  assessment_id,
  COUNT(DISTINCT assessment_category) AS category_count,
  string_agg(DISTINCT assessment_category, ', ' ORDER BY assessment_category) AS categories
FROM assessmentsapp__table__unified_assessments_pg
WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
GROUP BY assessment_id
ORDER BY assessment_id;
"
```

Stop and inspect manually if multiple unrelated assessment IDs already exist.

## 5. Repair Missing Assessment Rows If Needed

Only insert missing categories. Reuse the existing logical defaults from the
legacy replay path.

Architecture & Configuration insert:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
INSERT INTO assessmentsapp__table__unified_assessments_pg (
  assessment_id,
  platform_account_id,
  assessment_name,
  assessment_description,
  assessment_category,
  is_active,
  created_date,
  created_by,
  version,
  owner_name
)
SELECT
  '$ASSESSMENT_ID',
  '$PLATFORM_ACCOUNT_ID',
  'Default Assessment',
  'This assessment evaluates your assets against recommended best practices based on Cisco''s proven expertise. It detects configuration deviations across your infrastructure that may affect availability, security, or performance. Each best practice rule is evaluated across your covered assets, with findings prioritized by severity to help you ensure configuration consistency, enhance resilience, and reduce operational risk.',
  'Architecture & Configuration',
  true,
  NOW(),
  'cisco-iq-config-saas-skill-replay',
  1,
  'cisco-iq-config-saas-skill-replay'
WHERE NOT EXISTS (
  SELECT 1
  FROM assessmentsapp__table__unified_assessments_pg
  WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
    AND assessment_id = '$ASSESSMENT_ID'
    AND assessment_category = 'Architecture & Configuration'
);
"
```

Security insert:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
INSERT INTO assessmentsapp__table__unified_assessments_pg (
  assessment_id,
  platform_account_id,
  assessment_name,
  assessment_description,
  assessment_category,
  is_active,
  created_date,
  created_by,
  version,
  owner_name
)
SELECT
  '$ASSESSMENT_ID',
  '$PLATFORM_ACCOUNT_ID',
  'Default Assessment',
  'This assessment evaluates your assets against Cisco OS Hardening Guides. It detects configuration deviations across your infrastructure that may affect security posture, or risk exposure. Each security hardening rule is evaluated across your covered assets, with findings prioritized by severity to help you address security gaps, enhance resilience, and reduce operational risk.',
  'Security',
  true,
  NOW(),
  'cisco-iq-config-saas-skill-replay',
  1,
  'cisco-iq-config-saas-skill-replay'
WHERE NOT EXISTS (
  SELECT 1
  FROM assessmentsapp__table__unified_assessments_pg
  WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
    AND assessment_id = '$ASSESSMENT_ID'
    AND assessment_category = 'Security'
);
"
```

## 6. Generate a New `execution_id`

Generate the execution ID locally so the SQL insert and the payload JSON use
the same value:

```bash
EXECUTION_ID="exec-$(date -u +%Y%m%d-%H%M%S)-replay"
echo "$EXECUTION_ID"
```

If you are running multiple replays in the same second, append your own suffix.

## 7. Insert the Pending Execution Row (this is the trigger)

Mirrors `create_execution_entry_with_management_system` in
`assessment-unified-engine` (`src/cbp_engine/clients/database.py`) — the
same insert the producer runs for the DB Queue / KEDA pattern. The `payload`
column carries the UDM table names the worker needs; `engine_status =
'PENDING'` is what KEDA's PostgreSQL scaler polls for.

Build the payload JSON first (UDM table names from
[`table-registry.md`](table-registry.md); override `MANAGEMENT_SYSTEM_TYPE`
if known, e.g. `DNAC`, `MERAKI`):

```bash
MANAGEMENT_SYSTEM_TYPE=""   # e.g. DNAC; leave empty if unknown

PAYLOAD_JSON=$(python3 -c "
import json
print(json.dumps({
    'execution_id': '$EXECUTION_ID',
    'assessment_id': '$ASSESSMENT_ID',
    'platform_account_id': '$PLATFORM_ACCOUNT_ID',
    'management_system_id': '$MANAGEMENT_SYSTEM_ID',
    'management_system_type': '$MANAGEMENT_SYSTEM_TYPE',
    'udm_asset_table': 'assetsudm__table__udm_asset',
    'udm_asset_telemetry_table': 'assetsudm__table__udm_asset_telemetry',
    'udm_command_table': 'assetsudm__table__udm_device_command',
    'udm_software_table': 'assetsudm__table__udm_software',
    'udm_product_table': 'assetsudm__table__udm_product',
    'udm_contract_coverage_table': 'assetsudm__table__udm_contract_coverage',
}))
" | sed "s/'/''/g")
```

The execution table also tracks engine/ETL timing, the upstream ETL job id,
and DB-queue claim columns. For an internal skill replay (no ETL
notification), insert **empty** defaults for those; cbp-engine sets
`engine_started_at`, `worker_id`, `claimed_at`, `heartbeat_at` when a worker
claims the row.

| Column | Replay default | Who sets it later |
| --- | --- | --- |
| `engine_started_at` | empty (`NULL`) | cbp-engine worker on claim |
| `etl_started_at` | empty (`NULL`) | ETL lifecycle (not used on internal replay) |
| `etl_finished_at` | empty (`NULL`) | ETL lifecycle (not used on internal replay) |
| `etl_job_id` | empty (`''`) | ETL notification `etlJobId` when present |
| `worker_id`, `claimed_at`, `heartbeat_at` | empty (`NULL`) | cbp-engine worker on claim |
| `priority` | `1` | not changed by replay |

Optional — only when mirroring an ETL-driven execution:

```bash
ETL_JOB_ID=""   # e.g. etl job id from the upstream notification; leave empty for internal replay
```

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
INSERT INTO assessmentsapp__table__unified_assessments_execution_pg (
  execution_id,
  assessment_id,
  platform_account_id,
  management_system_id,
  management_system_type,
  started_at,
  finished_at,
  rules_count,
  assets_count,
  violations_count,
  executed_by,
  triggered_by_schedule,
  engine_status,
  etl_status,
  engine_started_at,
  etl_started_at,
  etl_finished_at,
  etl_job_id,
  payload,
  worker_id,
  claimed_at,
  heartbeat_at,
  priority
)
VALUES (
  '$EXECUTION_ID',
  '$ASSESSMENT_ID',
  '$PLATFORM_ACCOUNT_ID',
  '$MANAGEMENT_SYSTEM_ID',
  '$MANAGEMENT_SYSTEM_TYPE',
  NOW(),
  CAST(NULL AS TIMESTAMP WITH TIME ZONE),
  0,
  0,
  CAST(NULL AS INTEGER),
  'cisco-iq-config-saas-skill-replay',
  false,
  'PENDING',
  'PENDING',
  NULL,
  NULL,
  NULL,
  '',
  '$PAYLOAD_JSON',
  NULL,
  NULL,
  NULL,
  1
)
ON CONFLICT (execution_id) DO NOTHING;
"
```

When `ETL_JOB_ID` is set, replace the `''` etl_job_id value with the job id
(and consider setting `executed_by` to the same id so producer dedupe
behavior matches the ETL path):

```sql
  '$ETL_JOB_ID'
```

If the insert reports zero affected rows because of an ID collision, generate a
new `EXECUTION_ID` and retry once.

## 8. Read-Only Verification of the Inserted State

Verify the execution row immediately after insert. This is also your
trigger-confirmation step — the row exists with `engine_status = 'PENDING'`
means KEDA has something to poll; no further action is needed to trigger
processing.

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
SELECT
  execution_id,
  assessment_id,
  platform_account_id,
  management_system_id,
  management_system_type,
  engine_status,
  etl_status,
  executed_by,
  triggered_by_schedule,
  started_at,
  finished_at,
  engine_started_at,
  worker_id,
  claimed_at,
  heartbeat_at,
  priority,
  etl_started_at,
  etl_finished_at,
  etl_job_id
FROM assessmentsapp__table__unified_assessments_execution_pg
WHERE execution_id = '$EXECUTION_ID';
"
```

## 9. Watch the Claim (optional)

KEDA's PostgreSQL scaler (`pollingInterval`, default 10s) spawns a
`cbp-engine-worker-job` pod once its trigger activates. Re-run the Step 8
query after a short wait — `engine_status` should flip to `INPROGRESS` with
`worker_id`/`claimed_at`/`heartbeat_at` populated, then to
`COMPLETED`/`FAILED` when the job finishes.

**Activation threshold gotcha (verified live on dev and prod):** the
`cbp-engine-worker-job` ScaledJob's `activationTargetQueryValue` is `1` in
every env — KEDA only scales from zero when the `PENDING`-row count
**exceeds** that value (i.e. ≥ 2), not merely ≥ 1. A lone replay insert into
an otherwise-empty queue will sit at `engine_status = 'PENDING'` indefinitely
with `Is Active: false` on the ScaledJob. Before assuming a stuck replay,
check the current backlog and the trigger's live state:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
SELECT count(*) FROM assessmentsapp__table__unified_assessments_execution_pg
WHERE engine_status = 'PENDING';
"

KUBE_CONTEXT="cx-dev-usw2"
[ "$ENV" = "nprd" ] && KUBE_CONTEXT="cx-nprd-$REGION"
[ "$ENV" = "prod" ] && KUBE_CONTEXT="cx-prd-$REGION"
kubectl --context "$KUBE_CONTEXT" -n assessments-configuration \
  describe scaledjob cbp-engine-worker-job | grep -i "is active"
```

If the count is `1` (just your replay row) and `Is Active: false`, KEDA will
not spawn a worker until a second `PENDING` row appears — either real
traffic queues one, or you knowingly insert a second throwaway `PENDING`
row to cross the threshold (only do this with the user's explicit OK,
especially in prod). If it stays `PENDING` for more than a couple of KEDA
polling intervals despite the count being ≥ 2, check the KEDA `ScaledJob`
and any `cbp-engine-worker-job-*` pods in `assessments-configuration` for
scheduling or claim errors.

## Replay Contract Summary

1. collect explicit inputs
2. run read-only assessment derivation queries
3. repair missing assessment rows only if required
4. derive exactly one `ASSESSMENT_ID`
5. generate one `EXECUTION_ID`
6. build the `payload` JSON (UDM table names + IDs)
7. insert one pending execution row with `engine_status = 'PENDING'` and that
   `payload` — this insert **is** the trigger; KEDA's PostgreSQL scaler picks
   it up, no publish step
8. verify the inserted row, optionally watch it get claimed
