# Replay Assessment Execution

This runbook replays a single assessment execution through the skill-native
Config SaaS operator path.

It uses the bundled Postgres helper for all Aurora writes and reads:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" <env> [region] "<sql>"
```

It publishes through the native cbp-engine producer code path from a
`cbp-engine-producer` pod. This avoids custom Kafka credential parsing and uses
the same runtime configuration as the service:

```bash
kubectl --context "$KUBE_CONTEXT" -n assessments-configuration exec "$PRODUCER_POD" -- \
  python3 -c "from cbp_engine.clients.platform_kafka import send_assessment_execution; payload={...}; send_assessment_execution(payload)"
```

## Scope

This workflow intentionally performs controlled mutations:

1. create missing assessment rows if required
2. insert a pending execution row
3. publish the replay/internal execution notification

Use read-only verification first. For prod, stop and get explicit confirmation
before any INSERT or Kafka publish.

## Mandatory Inputs

- `env`
- `region` (`usw2`, `apse2`, `euc1` for `nprd`/`prod`; omit or use `usw2` for `dev`)
- `platform_account_id`
- `management_system_id`

Derived later:

- `assessment_id` from `assessmentsapp__table__assessments_pg`
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
kubectl --context "$KUBE_CONTEXT" -n assessments-configuration exec "$PRODUCER_POD" -- \
  python3 -c "from cbp_engine.clients.platform_kafka import send_assessment_execution; payload={...}; send_assessment_execution(payload)"
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
FROM assessmentsapp__table__assessments_pg
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
FROM assessmentsapp__table__assessments_pg
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
INSERT INTO assessmentsapp__table__assessments_pg (
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
  FROM assessmentsapp__table__assessments_pg
  WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
    AND assessment_id = '$ASSESSMENT_ID'
    AND assessment_category = 'Architecture & Configuration'
);
"
```

Security insert:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
INSERT INTO assessmentsapp__table__assessments_pg (
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
  FROM assessmentsapp__table__assessments_pg
  WHERE platform_account_id = '$PLATFORM_ACCOUNT_ID'
    AND assessment_id = '$ASSESSMENT_ID'
    AND assessment_category = 'Security'
);
"
```

## 6. Generate a New `execution_id`

Generate the execution ID locally so the SQL insert and Kafka publish use the
same value:

```bash
EXECUTION_ID="exec-$(date -u +%Y%m%d-%H%M%S)-replay"
echo "$EXECUTION_ID"
```

If you are running multiple replays in the same second, append your own suffix.

## 7. Insert the Pending Execution Row

Use the UA execution table when replaying in dev. Insert the full UA execution
table column set so the replay row matches the deployed schema.

**Critical:** The `payload_json` column MUST be populated. The DB Queue worker
(`_run_db_queue_worker`) reads `payload_json` when it claims an execution row.
If `payload_json` is NULL, the worker marks the execution as FAILED immediately
with "Claimed execution has no payload". The payload structure mirrors the
`db_payload` built by `cbp_engine.core.producer._process_external_notification`.

First, build the payload JSON string:

```bash
PAYLOAD_JSON=$(cat <<EOJSON
{"execution_id": "$EXECUTION_ID", "assessment_id": "$ASSESSMENT_ID", "platform_account_id": "$PLATFORM_ACCOUNT_ID", "management_system_id": "$MANAGEMENT_SYSTEM_ID", "management_system_type": "DNAC", "scenario": "cbp-slic-assessment", "udm_asset_table": "udm_asset_1__0__10", "udm_asset_telemetry_table": "udm_asset_telemetry_1__0__9", "udm_command_table": "udm_device_command_1__0__7", "udm_software_table": "udm_software_1__0__7", "udm_product_table": "udm_product_1__0__6", "udm_contract_coverage_table": "udm_contract_coverage_1__0__11"}
EOJSON
)
echo "$PAYLOAD_JSON"
```

Then insert with the payload:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
INSERT INTO assessmentsapp__table__ua_assessments_execution_pg (
  execution_id,
  platform_account_id,
  management_system_id,
  management_system_type,
  assessment_id,
  started_at,
  engine_started_at,
  finished_at,
  etl_started_at,
  etl_finished_at,
  etl_job_id,
  rules_count,
  assets_count,
  violations_count,
  executed_by,
  triggered_by_schedule,
  engine_status,
  etl_status,
  config_etl_status,
  sec_hrd_etl_status,
  payload,
  payload_json,
  worker_id,
  claimed_at,
  heartbeat_at,
  priority
)
VALUES (
  '$EXECUTION_ID',
  '$PLATFORM_ACCOUNT_ID',
  '$MANAGEMENT_SYSTEM_ID',
  'DNAC',
  '$ASSESSMENT_ID',
  NOW(),
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  0,
  0,
  NULL,
  'cisco-iq-config-saas-skill-replay',
  false,
  'PENDING',
  'PENDING',
  NULL,
  NULL,
  NULL,
  '$PAYLOAD_JSON',
  NULL,
  NULL,
  NULL,
  1
)
ON CONFLICT (execution_id) DO NOTHING;
"
```
If the insert reports zero affected rows because of an ID collision, generate a
new `EXECUTION_ID` and retry once.

### Payload field reference

| Field | Source | Notes |
| --- | --- | --- |
| `execution_id` | Generated in step 6 | Must match the row's `execution_id` column |
| `assessment_id` | Derived in steps 3–5 | Single assessment_id for the platform account |
| `platform_account_id` | User input | |
| `management_system_id` | User input | |
| `management_system_type` | Constant `"DNAC"` | Unless replaying a non-DNAC system |
| `scenario` | Constant `"cbp-slic-assessment"` | Determines SLIC worker path |
| `udm_asset_table` | Table registry | Currently `udm_asset_1__0__10` |
| `udm_asset_telemetry_table` | Table registry | Currently `udm_asset_telemetry_1__0__9` |
| `udm_command_table` | Table registry | Currently `udm_device_command_1__0__7` |
| `udm_software_table` | Table registry | Currently `udm_software_1__0__7` |
| `udm_product_table` | Table registry | Currently `udm_product_1__0__6` |
| `udm_contract_coverage_table` | Table registry | Currently `udm_contract_coverage_1__0__11` |

When UDM table versions are bumped, update the table registry
(`docs/table-registry.md`) and use the new names in `PAYLOAD_JSON`.

## 8. Read-Only Verification of the Inserted State

Verify the execution row immediately after insert:

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
  etl_started_at,
  etl_finished_at,
  etl_job_id,
  rules_count,
  assets_count,
  violations_count,
  config_etl_status,
  sec_hrd_etl_status,
  payload_json,
  worker_id,
  claimed_at,
  heartbeat_at,
  priority
FROM assessmentsapp__table__ua_assessments_execution_pg
WHERE execution_id = '$EXECUTION_ID';
"
```

## 9. Kafka Publish Step

The SQL insert only prepares the execution row. The replay is triggered by
publishing the internal execution message from a producer pod in the target
cluster.

**This step is mandatory.** Inserting the execution row without publishing means
the worker never picks it up. Both the DB INSERT (step 7) and the Kafka publish
(step 9) must complete for a valid replay.

### 9a. Resolve the producer pod

```bash
KUBE_CONTEXT="cx-${ENV/dev/dev}-${REGION}"
if [ "$ENV" = "prod" ]; then KUBE_CONTEXT="cx-prd-$REGION"; fi
if [ "$ENV" = "nprd" ]; then KUBE_CONTEXT="cx-nprd-$REGION"; fi
if [ "$ENV" = "dev" ]; then KUBE_CONTEXT="cx-dev-usw2"; fi

PRODUCER_POD="$(kubectl --context "$KUBE_CONTEXT" -n assessments-configuration get pods -l app=cbp-engine-producer -o jsonpath='{.items[0].metadata.name}')"
test -n "$PRODUCER_POD"
```

### 9b. Publish through native cbp-engine producer code

Use the service-native producer path from inside the producer pod. Do **not**
copy a custom Kafka helper into the pod. The native path reuses cbp-engine's
runtime Secrets Manager, APISIX messaging authorization, topic, TLS, and
credential handling.

```bash
kubectl --context "$KUBE_CONTEXT" -n assessments-configuration exec "$PRODUCER_POD" -- \
  env \
    PLATFORM_ACCOUNT_ID="$PLATFORM_ACCOUNT_ID" \
    MANAGEMENT_SYSTEM_ID="$MANAGEMENT_SYSTEM_ID" \
    ASSESSMENT_ID="$ASSESSMENT_ID" \
    EXECUTION_ID="$EXECUTION_ID" \
    python3 -c '
import os, json, logging, sys

# Enable INFO logging so httpx/SDK authorize responses are visible
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s", stream=sys.stdout)

from cbp_engine.clients.platform_kafka import send_assessment_execution

platform_account_id = os.environ["PLATFORM_ACCOUNT_ID"]
payload = {
    "execution_id": os.environ["EXECUTION_ID"],
    "customer_id": platform_account_id,
    "assessment_id": os.environ["ASSESSMENT_ID"],
    "platform_account_id": platform_account_id,
    "management_system_id": os.environ["MANAGEMENT_SYSTEM_ID"],
    "management_system_type": "DNAC",
    "scenario": "cbp-slic-assessment",
    "udm_asset_table": "udm_asset_1__0__10",
    "udm_asset_telemetry_table": "udm_asset_telemetry_1__0__9",
    "udm_contract_coverage_table": "udm_contract_coverage_1__0__11",
    "udm_product_table": "udm_product_1__0__6",
    "udm_software_table": "udm_software_1__0__7",
    "udm_command_table": "udm_device_command_1__0__7",
}

print("=" * 60)
print("REPLAY — Publishing internal execution notification")
print("=" * 60)
print(f"  Topic: assessmentsapp.execution.status")
print(f"  execution_id: {payload[\"execution_id\"]}")
print(f"  platform_account_id: {payload[\"platform_account_id\"]}")
print(f"  management_system_id: {payload[\"management_system_id\"]}")
print(f"  assessment_id: {payload[\"assessment_id\"]}")
print()
print("Payload:")
print(json.dumps(payload, indent=2))
print()

try:
    send_assessment_execution(payload)
    print()
    print("=" * 60)
    print("[OK] Message published successfully!")
    print(f"     execution_id: {payload[\"execution_id\"]}")
    print("=" * 60)
except Exception as e:
    print()
    print("=" * 60)
    print(f"[FAILED] Publish error: {e}")
    print("=" * 60)
    sys.exit(1)
'
```

Expected success output:

```text
============================================================
REPLAY — Publishing internal execution notification
============================================================
  Topic: assessmentsapp.execution.status
  execution_id: exec-20250625-manual-replay
  platform_account_id: TestCustomer1
  management_system_id: 91b30e45-...
  assessment_id: asmt-TestCust-2cbf62

Payload:
{
  "execution_id": "exec-20250625-manual-replay",
  ...
}

INFO httpx HTTP Request: POST https://apisix-gateway.apisix.svc.cluster.local/messaging/api/v1/authorize "HTTP/1.1 200 OK"
INFO cbp_engine.clients.platform_kafka Assessment execution sent: execution_id=exec-20250625-manual-replay, ...

============================================================
[OK] Message published successfully!
     execution_id: exec-20250625-manual-replay
============================================================
```

If publish fails, you will see `[FAILED] Publish error: <details>` and a
non-zero exit code. Do not paste credential-bearing logs into chat.

## 10. Post-Publish Verification

Re-check the execution row after publish:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" "$ENV" "$REGION" "
SELECT
  execution_id,
  assessment_id,
  platform_account_id,
  management_system_id,
  engine_status,
  etl_status,
  started_at,
  finished_at,
  engine_started_at,
  etl_started_at,
  etl_finished_at,
  etl_job_id
FROM assessmentsapp__table__assessments_execution_pg
WHERE execution_id = '$EXECUTION_ID';
"
```

If needed, inspect producer logs separately with a narrowly scoped grep for the
execution ID. Do not paste full sensitive log blocks into chat.

## Replay Contract Summary

1. collect explicit inputs
2. run read-only assessment derivation queries
3. repair missing assessment rows only if required
4. derive exactly one `ASSESSMENT_ID`
5. generate one `EXECUTION_ID`
6. insert one execution row using the UA execution table and its full column set
7. **publish one replay/internal message with native `send_assessment_execution` — mandatory**
8. verify the inserted row and publish outcome
