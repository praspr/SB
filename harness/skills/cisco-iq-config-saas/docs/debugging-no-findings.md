# Debugging — Customer Has No Findings

Use this runbook when a customer reports no findings in ConfigBP and you
need to identify where in the pipeline data is missing.

The pipeline (high level):

```text
connector / ETL  →  Kafka notifications  →  cbp-engine producer
  →  Aurora assessment + execution rows  →  cbp-engine worker
  →  UDM Iceberg eligibility + SLIC evaluation
  →  Aurora finding / recommendation / insight rows  →  configbp-ai agent
```

Walk the pipeline from output backward. Stop at the first stage that has
no data.

## Step 1 — Aurora: assessment, execution, tracking

Run against the target env/region with the bundled helper. Substitute the
`platform_account_id` you are investigating.

```bash
# Any assessments?
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 \
  "SELECT assessment_id, assessment_name, is_active, created_date
   FROM assessmentsapp__table__unified_assessments_pg
   WHERE platform_account_id = '<platform_account_id>'
   ORDER BY created_date DESC LIMIT 10;"

# Any executions?
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 \
  "SELECT execution_id, started_at, finished_at, engine_status, etl_status,
          rules_count, assets_count, violations_count
   FROM assessmentsapp__table__unified_assessments_execution_pg
   WHERE platform_account_id = '<platform_account_id>'
   ORDER BY started_at DESC LIMIT 10;"

# Any connector execution tracking?
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 \
  "SELECT *
   FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
   WHERE platform_account_id = '<platform_account_id>'
   ORDER BY updated_at DESC LIMIT 10;"
```

Interpretation:

| Result                                         | Likely cause                                                            | Next step |
|------------------------------------------------|-------------------------------------------------------------------------|-----------|
| All three return 0 rows                        | cbp-engine producer never received a notification for this account     | Skip to Step 2 (confirm UDM exists) and then check connector/ETL upstream |
| Executions exist, `violations_count = 0`       | Engine ran but found no eligible devices or no rule matched            | Go to Step 2 to confirm UDM eligibility |
| Executions exist with errors in `engine_status` / `etl_status` | Worker or ETL failure                                | Inspect cbp-engine worker logs and the cited error fields |
| Findings exist but UI / agent shows none       | Stale agent cache, Expert Insights path, or downstream MCP issue       | Inspect configbp-ai MCP/agent cache and expert-insights flow |

## Step 2 — UDM Iceberg eligibility (cbp-engine worker view)

This mirrors the exact UDM query the cbp-engine worker runs
(`_fetch_device_telemetry` + `_fetch_device_commands_batch` in `worker.py`).

Devices must pass **all** of these to be eligible:

- `software_type` ∈ `{IOS, IOS-XE, IOS XR, NX-OS, AireOS}`
- `cx_level >= 10` (active CX contract)
- For `AireOS`: `product_id LIKE 'AIR-CT%'`
- At least one **successful** show-command output in `udm_device_command`
  for the SLIC command set.

### UDM table names

The query below uses the unversioned `assetsudm__table__udm_*` names
`cbp-engine` itself reads (see [`table-registry.md`](table-registry.md)),
not the version-pinned `udm_*_1__0__N` names — no version bump to track.

### Full SLIC eligibility query (prod usw2 shown)

```bash
bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod usw2 "
SELECT
    dc.asset_key,
    ARRAY_AGG(DISTINCT dc.command) AS commands,
    COUNT(DISTINCT dc.command)     AS command_count
FROM assetsudm__table__udm_device_command dc
INNER JOIN assetsudm__table__udm_asset_telemetry tel
    ON  dc.asset_key     = tel.asset_key
    AND dc.partition_key = tel.partition_key
WHERE dc.asset_key IN (
    SELECT DISTINCT a.asset_key
    FROM assetsudm__table__udm_asset_telemetry t
    INNER JOIN assetsudm__table__udm_software s
        ON  t.software_key = s.software_key
        AND t.platform_account_id = '<platform_account_id>'
        AND s.software_type IN ('IOS', 'IOS-XE', 'IOS XR', 'NX-OS', 'AireOS')
    INNER JOIN assetsudm__table__udm_contract_coverage c
        ON  t.serial_number = c.serial_number
        AND t.partition_key = c.partition_key
        AND TRY_CAST(c.cx_level AS INTEGER) >= 10
    INNER JOIN assetsudm__table__udm_asset a
        ON  t.asset_key     = a.asset_key
        AND t.partition_key = a.partition_key
    INNER JOIN assetsudm__table__udm_product p
        ON a.product_id = p.product_id
    WHERE s.software_type != 'AireOS'
       OR a.product_id LIKE 'AIR-CT%'
)
  AND dc.command IN (
        'show running-config',
        'show version',
        'show module',
        'show interface',
        'show inventory',
        'show run-config',
        'show tech-support wireless')
  AND dc.command_status = 'Success'
  AND dc.command_response IS NOT NULL
  AND TRIM(dc.command_response) <> ''
GROUP BY dc.asset_key
ORDER BY command_count, dc.asset_key
"
```

### Interpreting Step 2 results

| Outcome           | Meaning                                                                                                   | Action                                                                            |
|-------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| 0 rows            | No eligible devices: connector never synced, software type unsupported, `cx_level < 10`, or no command outputs | Escalate to connector / ETL team; verify the customer is in scope for SLIC       |
| Rows returned     | Eligible devices exist with command data                                                                  | cbp-engine should have processed them — check Kafka topics and producer/worker logs |

### Other regions

Swap the `run_iceberg_query.sh` `<env> [region]` args — the Glue database
and output bucket resolve automatically:

```bash
bash "$SKILL_DIR/scripts/run_iceberg_query.sh" nprd apse2 "..."
bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod euc1 "..."
```

## Step 3 — When everything in Step 1 and Step 2 looks healthy

If executions, eligible devices, and `udm_device_command` outputs all
exist but findings are missing or stale, inspect:

- cbp-engine worker logs in `assessments-configuration` namespace for the
  target env/region.
- configbp-ai MCP server and agent-side response cache for the
  `platform_account_id`.
- Expert Insights pipeline output, if the customer is using that surface.

Do not paste full customer data into chat. Prefer counts, schemas, and
redacted summaries.

## Step 4 — Finding exists in DB but invisible via the API

Use this path when `findings exist with violations_count > 0` but a
specific `findingId` (or all findings for a rule) returns nothing from the
`findings` GraphQL resolver.

The `findings` resolver requires `EXISTS(CVI CONNECTED)` — any finding
whose asset is absent from, or DISCONNECTED in, `cvi_assets_view` is
silently dropped.

### 4a — Confirm the findingId exists at all

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT finding_id, platform_account_id, asset_key, management_system_id,
       execution_id, finding_type, source_id, detected_at
FROM assessmentsapp__table__unified_config_assmt_finding_pg
WHERE finding_id = '<finding_id>'
LIMIT 5;"
```

| Result | Meaning |
|---|---|
| 0 rows | findingId does not exist in this region — check other regions |
| Rows returned | Proceed to 4b |

### 4b — Is the finding in the latest execution?

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT f.finding_id, f.execution_id,
       f.execution_id IN (
         SELECT latest_execution_id
         FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
         WHERE platform_account_id = '<paid_from_4a>'
       ) AS is_latest_execution,
       f.asset_key, f.management_system_id, f.finding_type
FROM assessmentsapp__table__unified_config_assmt_finding_pg f
WHERE f.finding_id = '<finding_id>';"
```

| Result | Meaning |
|---|---|
| `is_latest_execution = false` | findingId is stale — belongs to a prior execution. The API only shows current executions. Nothing to fix; the finding is legitimately old. |
| `is_latest_execution = true` | Finding is current — proceed to 4c |

### 4c — CVI connectivity check (exact mgmt ID match)

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT a.id, a.management_system_id, a.connectivity, a.hostname, a.ip_address
FROM assets__table__cvi_assets_view a
WHERE a.id = '<asset_key_from_4a>'
  AND a.management_system_id = '<management_system_id_from_4a>'
  AND a.platform_account_id = '<paid_from_4a>';"
```

| Result | Meaning |
|---|---|
| 1 row, `connectivity = CONNECTED` | CVI match is fine — finding should be visible. Check resolver SQL or MCP tool. |
| 1 row, `connectivity = DISCONNECTED` | Asset is genuinely disconnected. API correctly hides it. |
| 0 rows | Management system ID mismatch — proceed to 4d |

### 4d — CVI check without mgmt ID (detect mgmt drift)

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT a.id, a.management_system_id, a.connectivity, a.hostname, a.ip_address
FROM assets__table__cvi_assets_view a
WHERE a.id = '<asset_key_from_4a>'
  AND a.platform_account_id = '<paid_from_4a>'
LIMIT 10;"
```

| Result | Meaning |
|---|---|
| 0 rows | Asset is completely absent from CVI for this account. Data pipeline issue. |
| Rows with **different** `management_system_id` than findings | **Management system ID drift** — see below |

### 4e — Investigate stale exec_track rows

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT management_system_id, latest_execution_id, updated_at
FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
WHERE platform_account_id = '<paid>'
ORDER BY updated_at DESC;"
```

Compare `updated_at` ages. Any row significantly older than the newest
active rows is a stale connector registration — see below.

---

### Root cause: Management system ID drift

When a connector is replaced or re-registered, the new instance gets a
different `management_system_id`. CVI updates to the new ID immediately.
The old findings table rows keep the old ID permanently.

```
Old connector:  findings.management_system_id = 55d20c35  (orphaned)
New connector:  cvi_assets_view.management_system_id = 019ed5dc  (active)

findings JOIN/EXISTS on management_system_id → mismatch → 0 results
```

**Verification:** Confirm the active mgmt ID has findings for this asset:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT COUNT(*) AS finding_count, MIN(detected_at), MAX(detected_at)
FROM assessmentsapp__table__unified_config_assmt_finding_pg
WHERE management_system_id = '<new_mgmt_id_from_cvi>'
  AND asset_key = '<asset_key>'
  AND platform_account_id = '<paid>';"
```

- `0 rows` → drift happened before a new assessment ran. The asset will
  become visible after the next assessment run under the new mgmt ID.
- `> 0 rows` → the new mgmt ID has fresh findings. The invisible findingId
  belongs to the old run only. Check if the new run has the same violation.

### Root cause: Stale exec_track rows inflating counts

When `assetsEvaluatedCount` (from `ruleEvaluations`) is higher than
`findingsCount` (from `findingsCount` resolver), the gap is caused by
stale exec_track rows. The `exec_ids` CTE returns **all** management
system rows for the account — including old, decommissioned ones.

Those old execution findings are counted in the `DISTINCT ON` dedup but
dropped by `EXISTS(CVI CONNECTED)` because the old mgmt ID is no longer
in CVI.

**Quantify the gap by management system:**

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
WITH exec_ids AS MATERIALIZED(
  SELECT latest_execution_id, management_system_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = '<paid>'
),
deduped AS (
  SELECT DISTINCT ON (f.management_system_id, f.asset_key, f.source_id)
    f.management_system_id, f.asset_key
  FROM assessmentsapp__table__unified_config_assmt_finding_pg f
  WHERE f.execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
    AND f.platform_account_id = '<paid>'
    AND f.source_id = '<rule_id>'
  ORDER BY f.management_system_id, f.asset_key, f.source_id DESC
)
SELECT d.management_system_id,
       COUNT(*) AS asset_count,
       COUNT(CASE WHEN EXISTS(
         SELECT 1 FROM assets__table__cvi_assets_view a
         WHERE a.id = d.asset_key AND a.management_system_id = d.management_system_id
           AND a.platform_account_id = '<paid>' AND a.connectivity = 'CONNECTED'
       ) THEN 1 END) AS cvi_matched,
       COUNT(CASE WHEN NOT EXISTS(
         SELECT 1 FROM assets__table__cvi_assets_view a
         WHERE a.id = d.asset_key AND a.management_system_id = d.management_system_id
           AND a.platform_account_id = '<paid>' AND a.connectivity = 'CONNECTED'
       ) THEN 1 END) AS cvi_no_match
FROM deduped d
GROUP BY d.management_system_id
ORDER BY asset_count DESC;"
```

Any `management_system_id` with `cvi_no_match > 0` and a stale
`updated_at` in `exec_track` is a stale row contributing to the count gap.

**Fix:** Remove the stale `exec_track` row or trigger a fresh assessment
under the active management system ID so findings are re-written with the
correct mgmt ID.
