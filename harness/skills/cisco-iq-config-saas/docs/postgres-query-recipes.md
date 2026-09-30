# Postgres Query Recipes

Helper-level patterns for `run_postgres_query.sh`. For table names see
[`table-registry.md`](table-registry.md). For env/region matrix see
[`SKILL.md`](../SKILL.md) (Environment Matrix).

## Helper invocation

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" <env> [region] [flags] "<sql>"
```

The script automatically:

- selects the right kubectl context (see context naming below)
- uses namespace `sre-baseapps` for the debug pod
- locates the debug pod used for DB access
- reads DB connection values from the relevant in-cluster secret
- opens `psql` or runs a one-shot SQL query

It also auto-refreshes AWS auth when needed, so you do not need to
pre-run `duo-sso`.

### Kubernetes context naming

`env` + `region` resolve to a team-standard kubeconfig alias:
`cx-dev-usw2`, `cx-nprd-<region>`, `cx-prd-<region>` (note **`cx-prd-`**,
not `cx-prod-`). These aliases are created by the bundled, lightweight
helper:

```bash
bash "$SKILL_DIR/scripts/setup_kube_context.sh" <env> [<region>]
```

`setup_kube_context.sh` does not require sudo, does not start a
port-forward, and is a no-op if the alias already reaches the cluster.
Run it once per target on a new laptop. There is no need to start
`local_apisix_setup.sh` (which is sudo + port-forward + foreground)
just to get the alias — that script is only for ad hoc APISIX/Trino
debugging.

If your kubeconfig already uses a non-standard context for the same
EKS cluster, you can set `KUBE_CONTEXT=<your-context>` per call to skip
the alias lookup entirely. See [`../SKILL.md`](../SKILL.md) →
"Kubernetes Context Naming (Team-Wide)" for the full matrix and
override semantics. Per-target credential caches are written to
`$SKILL_DIR/.cache/postgres/<context>.env` and are local-only
(gitignored, never share or commit).

## Excel output (opt-in)

Excel / CSV generation is **OFF by default**. One-shot queries print to
the terminal only and do not create any files unless you opt in.

| How to enable                         | Effect                                                          |
|---------------------------------------|-----------------------------------------------------------------|
| `--excel` or `-x` on the command line | Generate `query_outputs/*.xlsx` for this call only              |
| `EXCEL_OUTPUT=1` env var              | Generate `.xlsx` for every call in that shell                   |
| `--no-excel`                          | Force-disable, even if `EXCEL_OUTPUT=1` is set                  |
| `OUTPUT_DIR=/some/path`               | Override the output directory (default `query_outputs`)         |

Examples:

```bash
# Terminal only
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "select 1;"

# Terminal + .xlsx for this call only
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 --excel "select 1;"

# Short flag form
bash "$SKILL_DIR/scripts/run_postgres_query.sh" -x dev "select 1;"

# Global opt-in for the shell
EXCEL_OUTPUT=1 bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 "select 1;"

# Env opt-in but this call off
EXCEL_OUTPUT=1 bash "$SKILL_DIR/scripts/run_postgres_query.sh" dev --no-excel "select 1;"
```

The flag is positional-agnostic — it works before, between, or after the
env/region tokens.

### When to use `--excel`

- **Default**: no `--excel`. For routine investigations and ad-hoc reads,
  quoting results into chat is enough.
- Add `--excel` only when:
  - The user explicitly asks for an exported file.
  - The result set is large enough that the user will realistically want
    to open it in Excel later.

## SQL safety rules

- Production is **read-only by policy**. Use `SELECT` only. Never run
  `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER`, `DROP`, or any DDL
  against prod.
- Always use `LIMIT` on exploratory prod queries to avoid expensive scans.
- Treat any prod row data as customer-sensitive. Do not paste raw rows
  into chat unless the user explicitly asks. Prefer counts, schemas, and
  redacted summaries.

## Recipe — Latest execution IDs for a `platformAccountId`

A single `platformAccountId` can have multiple latest execution IDs —
typically one per `management_system_id`.

Template (substitute live table names from
[`table-registry.md`](table-registry.md)):

```sql
SELECT
    t.management_system_id,
    t.latest_execution_id,
    e.finished_at
FROM <execution_tracking_table> t
LEFT JOIN <execution_table> e
    ON e.execution_id        = t.latest_execution_id
   AND e.platform_account_id = t.platform_account_id
WHERE t.platform_account_id = ?
ORDER BY t.management_system_id;
```

Concrete version using current Config SaaS table names:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 "
SELECT
    t.management_system_id,
    t.latest_execution_id,
    e.finished_at
FROM assessmentsapp__table__unified_cust_connector_exec_track_pg t
LEFT JOIN assessmentsapp__table__unified_assessments_execution_pg e
    ON e.execution_id        = t.latest_execution_id
   AND e.platform_account_id = t.platform_account_id
WHERE t.platform_account_id = '<platform_account_id>'
ORDER BY t.management_system_id;
"
```

## Recipe — Row counts per Config SaaS table (target env/region)

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 \
  "SELECT count(*) FROM assessmentsapp__table__unified_assessments_pg;"

bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 \
  "SELECT count(*) FROM assessmentsapp__table__unified_assessments_execution_pg;"

bash "$SKILL_DIR/scripts/run_postgres_query.sh" nprd usw2 \
  "SELECT count(*) FROM assessmentsapp__table__unified_config_assmt_finding_pg;"
```

## Recipe — Per-account counts across the pipeline

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod usw2 "
SELECT
  (SELECT count(*) FROM assessmentsapp__table__unified_assessments_pg
     WHERE platform_account_id = '<platform_account_id>')           AS assessments,
  (SELECT count(*) FROM assessmentsapp__table__unified_assessments_execution_pg
     WHERE platform_account_id = '<platform_account_id>')           AS executions,
  (SELECT count(*) FROM assessmentsapp__table__unified_config_assmt_finding_pg
     WHERE platform_account_id = '<platform_account_id>')           AS findings;
"
```

## Recipe — exec_track: all management systems for an account

Shows every management system registered for an account, their latest
execution IDs, and how stale each is. Useful for diagnosing count
discrepancies and finding invisible findings.

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT management_system_id, latest_execution_id, updated_at,
       NOW() - updated_at AS age
FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
WHERE platform_account_id = '<platform_account_id>'
ORDER BY updated_at DESC;"
```

Rows with `age` of several days or more while other rows are fresh
indicate **stale connector registrations** that were never cleaned up.
See [`debugging-no-findings.md`](debugging-no-findings.md) §Step 4 for
the full diagnostic.

## Recipe — BAQS resolver validation suite

Use these 8 queries to validate BAQS resolver behaviour for a specific
account and rule. Run them in order — the cross-checks in the validation
table below require results from multiple queries.

Replace `<PAID>`, `<RULE_ID>`, `<ASSET_KEY>`, `<FINDING_ID>` throughout.

For the full SQL and explanation of each query, see
[`baqs-resolvers.md`](baqs-resolvers.md) §8.

### Quick invocation pattern (one query at a time)

```bash
ENV=prod
REGION=apse2
PAID="ba8c95a8-2086-45ee-a326-cba28f7f1e93"
RULE_ID="16d0d7b8-14aa-478c-8657-5b87d2c6ba2c"
ASSET_KEY="91659b9ec035b06ebea0c0dc85f9dd08"
FINDING_ID="67b98d3b-8b9a-46a5-8df1-73251d3cbafe"

bash "$SKILL_DIR/scripts/run_postgres_query.sh" $ENV $REGION "
-- Q8: findingsCount
WITH exec_ids AS MATERIALIZED(
  SELECT latest_execution_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = '$PAID'
)
SELECT COUNT(*) AS totalCount
FROM assessmentsapp__table__unified_config_assmt_finding_pg f
WHERE f.execution_id IN (SELECT latest_execution_id FROM exec_ids)
  AND f.platform_account_id = '$PAID'
  AND f.source_id = '$RULE_ID'
  AND EXISTS (
    SELECT 1 FROM assets__table__cvi_assets_view a
    WHERE a.id = f.asset_key AND a.management_system_id = f.management_system_id
      AND a.platform_account_id = f.platform_account_id AND a.connectivity = 'CONNECTED'
  );"
```

### Validation checks

After running all 8 queries, apply:

| Check | Queries | Pass condition | Fail means |
|---|---|---|---|
| V1 | Q1 vs Q4/Q5 | `assetsCount >= assetsEvaluatedCount` | Multi-mgmt inflation (same physical asset counted twice) |
| V2 | Q4/Q5 vs Q8 | `assetsEvaluatedCount == findingsCount` | Gap = disconnected assets or stale exec_track rows |
| V3 | All | All timings < 2000 ms | SLA violation |
| V4 | Q4 vs Q5 | Same `assetsEvaluatedCount` | Path B/C inconsistency |

**V2 gap > 0:** Break down by management system to find the source:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
WITH exec_ids AS MATERIALIZED(
  SELECT latest_execution_id, management_system_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = '<PAID>'
),
deduped AS (
  SELECT DISTINCT ON (f.management_system_id, f.asset_key, f.source_id)
    f.management_system_id, f.asset_key
  FROM assessmentsapp__table__unified_config_assmt_finding_pg f
  WHERE f.execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
    AND f.platform_account_id = '<PAID>'
    AND f.source_id = '<RULE_ID>'
  ORDER BY f.management_system_id, f.asset_key, f.source_id DESC
)
SELECT d.management_system_id,
       COUNT(*) AS asset_count,
       COUNT(CASE WHEN EXISTS(
         SELECT 1 FROM assets__table__cvi_assets_view a
         WHERE a.id = d.asset_key AND a.management_system_id = d.management_system_id
           AND a.platform_account_id = '<PAID>' AND a.connectivity = 'CONNECTED'
       ) THEN 1 END) AS cvi_matched,
       COUNT(CASE WHEN NOT EXISTS(
         SELECT 1 FROM assets__table__cvi_assets_view a
         WHERE a.id = d.asset_key AND a.management_system_id = d.management_system_id
           AND a.platform_account_id = '<PAID>' AND a.connectivity = 'CONNECTED'
       ) THEN 1 END) AS cvi_no_match
FROM deduped d
GROUP BY d.management_system_id ORDER BY asset_count DESC;"
```

Any `management_system_id` row with `cvi_no_match > 0` and a stale
`updated_at` in `exec_track` is a ghost row driving the gap.

## Workflow — Before writing SQL

1. Open [`table-registry.md`](table-registry.md). Confirm the logical →
   physical table mapping for the env/region you are about to query.
2. If the user has shared updated `TRINO_TABLE_*` values, update the
   registry in-place (per the registry's update protocol) and use the new
   names in your query. Do not silently use stale names.
3. Use `SELECT` + `LIMIT` for exploration. Add `--excel` only on explicit
   request.
4. For BAQS resolver SQL, read [`baqs-resolvers.md`](baqs-resolvers.md)
   before writing any resolver-level queries. The dedup key, CTE patterns,
   and JOIN order matter for correctness and performance.
