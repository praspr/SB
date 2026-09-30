# BAQS Resolvers — Architecture & SQL Optimization

BAQS (Business API Query Service) is Cisco CX Platform's data-consumption
layer. It exposes platform entities through a **single unified GraphQL
endpoint**. Config SaaS registers **13 resolvers** in
`cxp-assmt-unified-plat-comp/lifecycle/baqs/baqs.json`.

This document covers the full architecture, the four highest-traffic
resolvers, SQL optimization patterns derived from production investigations
(July 2026), and key context from the BAQS platform itself.

---

## 1. Architecture Overview

### Request flow

```
┌────────────────┐
│  GraphQL       │   query FindingDetails($findingId: String!) { ... }
│  client (UI /  │
│  configbp-ai)  │
└───────┬────────┘
        │ HTTPS POST /graphql
        ▼
┌────────────────────────────────────────────────┐
│  BAQS runtime                                  │
│  1. Parse query against merged schema          │
│  2. Validate: types/fields exist? args match?  │
│  3. Dispatch to resolver:                      │
│     resolverQueries.query.<name>.sql  → Trino/PostgreSQL
│  4. Substitute {{paramName}} with inputs       │
│  5. Substitute ${LC.*} with lifecycle env vars │
│  6. Assemble response in the shape of query    │
└───────┬────────────────────────────────────────┘
        ▼
┌────────────────┐
│  { data: …,    │
│    errors: … } │
└────────────────┘
```

The schema is built once at registration time; resolvers fire per-request.

### Config structure

A BAQS config (`baqs.json`) has four top-level keys:

```jsonc
{
  "applicationId": "<UUID>",
  "entities":        [ /* GraphQL type definitions */ ],
  "query":           [ /* root query declarations */ ],
  "resolverQueries": { /* SQL resolvers, mirrors schema shape */ }
}
```

**Live snapshot for Config SaaS** (`applicationId: d92acbf7-…`):

| Element | Count | Notes |
|---|---|---|
| `entities` | 10 | `Assessment`, `Finding`, `RuleEvaluation`, `Count`, `ExpertInsight`, … |
| `query` (root) | 13 | `assessments`, `assessmentExecutions`, `ruleEvaluations`, `findings`, `findingsCount`, `findingFilterValues`, `recommendations`, `expertInsights`, `expertInsightsCount`, … |
| `mutation` | **0** | None — read-only against BAQS. Trino cannot return values from INSERT/UPDATE/DELETE, only a Boolean. Write paths go through app services directly. |
| `resolverQueries.query` | 13 | One per root query. All use `isFastLane: true, catalog: "postgresql"` |
| Nested resolvers | 0 | All data assembled in single-resolver SQL; no `resolverQueries.<Type>.<field>` |

### FastLane / PostgreSQL-only

All 13 resolvers declare:

```json
"isFastLane": true,
"catalog": "postgresql"
```

They **bypass Trino** and execute directly against the Aurora Postgres
consumption tables via JDBC. This means:

- Standard PostgreSQL dialect only — no Trino-specific syntax (`UNNEST`,
  `WITH ORDINALITY`, `APPROX_DISTINCT`, etc.)
- `LATERAL`, `ANY(array)`, `INTERVAL '7 days'`, and window functions are
  all valid PostgreSQL
- `DISTINCT ON` is PostgreSQL-specific and works correctly here

### Handlebars templates — `{{paramName}}` not `:argName`

Resolver SQL is a **Handlebars template** rendered at query time. This is
different from the generic BAQS `:argName` binding style described in
platform docs — our resolvers use the Handlebars form exclusively:

```handlebars
{{paramName}}                                   ← bind parameter value (no :argName)
{{#if args.paramName}} ... {{/if}}              ← conditional block
{{#if (eq args.assessmentCategory "Configuration")}} ... {{/if}}
{{#each args.tags}} '{{this}}' = ANY(a.tags) {{/each}}
```

**Key rule:** `args.` prefix is only used inside `{{#if}}` checks; bind
sites use `{{paramName}}` without `args.`.

**Built-in Handlebars helpers available in BAQS:**

| Helper | Usage |
|---|---|
| `{{> relativeDateFilter column='col' value=args.x}}` | Date range partial — emits `col >= :start AND col <= :end` |
| `{{#if (dateRangeValid args.x)}} ... {{/if}}` | Guard before using `relativeDateFilter` |
| `{{pagination args.offset args.limit}}` | Emits `OFFSET ? LIMIT ?` in one shot |
| `{{orderBy args.sortBy args.sortDirection}}` | Emits `ORDER BY col ASC/DESC` |
| `{{#if (exists args.x)}} ... {{/if}}` | Checks if arg is present (not null/undefined) |
| `{{#if (or args.a args.b)}} ... {{/if}}` | Logical OR across multiple args |

### `${LC.*}` table-name placeholders

Table names are never hard-coded. Every reference uses `${LC.VAR_NAME}`,
resolved from the lifecycle env file at deploy time:

```
${LC.APP_CONFIG_FINDINGS_CONSUMPTION_TABLE}
  → assessmentsapp__table__unified_config_assmt_finding_pg

${LC.CVI_ASSETS_VIEW_CONSUMPTION_TABLE}
  → assets__table__cvi_assets_view
```

See `cxp-assmt-unified-plat-comp/lifecycle/lifecycle_envs/<env>.env` for
the full mapping. The physical names are identical across dev, nprd, and
prod in all regions.

### Config vs SecurityHardening parallel families

Every resolver that touches findings or recommendations branches on
`assessmentCategory`:

```handlebars
{{#if (eq args.assessmentCategory "Configuration")}}
  ${LC.APP_CONFIG_FINDINGS_CONSUMPTION_TABLE}
{{else if (eq args.assessmentCategory "SecurityHardening")}}
  ${LC.APP_SEC_HRD_FINDINGS_CONSUMPTION_TABLE}
{{/if}}
```

When editing resolver SQL, always update **both** branches.

### Cross-cutting table patterns

- **`assessmentsapp__table__unified_*` is the current naming** — un-versioned
  suffix. Legacy `configuration_*_pg_0__1__15` and `sec_hrd_*_pg_0__0__11`
  names still exist in dev but are not read by BAQS.
- **Dual-category split:** every Config table (`config_assmt_finding_pg`,
  `config_assmt_recommendation_pg`) has a SecurityHardening mirror
  (`sec_hrd_assmt_finding_pg`, `sec_hrd_assmt_recommendation_pg`) with
  identical schema.
- **Dual-table pattern:** each entity has a datalake Iceberg table and a
  `_pg` consumption copy. BAQS only reads the `_pg` side.
- **Customer scoping:** every table has `(platform_account_id,
  management_system_id)` indexed. Every WHERE clause must filter on both.
- **CVI join hot-spot:** `assets__table__cvi_assets_view` has 68 indexes
  all leading with `platform_account_id`. There is no composite index on
  `(id, management_system_id)` — the actual JOIN key. The planner uses
  `(platform_account_id, id)` and re-checks `management_system_id` at
  runtime. Passing `f.platform_account_id` in the JOIN ON clause is
  critical for activating this index path.

### GraphQL essentials (quick reference)

Full primer: `ciq/docs/BAQS.md` §4. For engineers new to GraphQL:

- **Schema = contract** — requests are rejected for unknown types/fields.
  Clients pick exactly the fields they want; response mirrors the shape.
- **Types:** scalars (`String`, `Int`, `ID`), object types, `[List]`, `!` non-null
- **Input types** (`"type": "input"` in entities) — for structured arguments
  beyond scalars. Required for filter objects like `DateFilterInput`.
- **Mutations** — BAQS supports them but we declare 0. Trino can't return
  structured data from writes; write paths go through services directly.

---

## 2. The Multi-Management-System Model

This is the single most important concept for writing correct BAQS SQL.

### One account → multiple management systems

A single `platform_account_id` can be managed by several Catalyst Center
instances (or other connectors). Each connector runs its own assessment
execution independently.

The `exec_track` table stores **one row per (platform_account_id,
management_system_id) pair**:

```sql
SELECT management_system_id, latest_execution_id, updated_at
FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
WHERE platform_account_id = '<paid>'
ORDER BY updated_at DESC;
```

A typical multi-mgmt account:

| management_system_id | latest_execution_id | updated_at |
|---|---|---|
| `019ed5dc-…` | `exec-20260723-replay-mgmt2` | 2026-07-23 |
| `23e1ab6d-…` | `exec-20260723-replay-mgmt1` | 2026-07-23 |
| `55d20c35-…` | `exec-20260714-bb465f` | 2026-07-14 ← stale |

### The `exec_ids` CTE pattern

Every resolver scopes data to current executions using:

```sql
WITH exec_ids AS MATERIALIZED (
  SELECT latest_execution_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = {{platformAccountId}}
)
```

This returns **all management systems' latest executions** — not just one.
Both active and stale exec_track rows are included.

### Correct dedup key: `(management_system_id, asset_key, source_id)`

The findings table can have multiple rows for the same `(asset_key,
source_id)` pair if the asset is monitored by two different management
systems. The correct deduplication key is:

```sql
-- CORRECT: preserves one row per (mgmt × asset × rule) evaluation
DISTINCT ON (management_system_id, asset_key, source_id)

-- WRONG: collapses both management systems' evaluations into one row
DISTINCT ON (platform_account_id, asset_key, source_id)

-- WRONG: undercounts when same asset is in two management systems
COUNT(DISTINCT asset_key)
```

Validated on prod data: for any account where `exec_ids` returns one
execution per management system:

```
COUNT(*) = COUNT(DISTINCT (management_system_id, asset_key))
```

`COUNT(DISTINCT asset_key)` alone undercounts — confirmed in USW2 NPRD
where 1 asset in 2 mgmt systems gave `COUNT(DISTINCT asset_key) = 54`
vs correct count `55`.

### Stale exec_track rows

When a connector re-registers under a new management system ID:

- Old row stays in `exec_track` indefinitely (never auto-cleaned)
- `exec_ids` CTE includes it → findings from old execution appear in
  `assetsEvaluatedCount`
- BUT if the old mgmt ID no longer exists in CVI, those findings are
  dropped by the `EXISTS(CVI CONNECTED)` filter → `findingsCount` is lower
- **Gap = stale mgmt system asset count for the rule**

Diagnose with:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" prod apse2 "
SELECT management_system_id, latest_execution_id, updated_at
FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
WHERE platform_account_id = '<paid>'
ORDER BY updated_at DESC;"
```

Compare `updated_at` ages. Rows more than a few days older than the
newest are candidates for stale-row investigation.

---

## 3. Resolver: `assessmentExecutions`

Returns the assessment banner: `rulesCount`, `executedAt`, `assetsCount`.

### assetsCount — UNION ALL hybrid

The old approach (`COUNT(DISTINCT asset_key) FROM asset_mdata`) failed when
a management system produced findings but no `asset_mdata` rows — causing
`assetsCount` to undercount (observed: EUC1 reporting 73 instead of 147).

Current approach:

```sql
SELECT SUM(asset_count) FROM (
  -- Fast path: management systems that have asset_mdata rows
  SELECT execution_id, COUNT(DISTINCT asset_key) AS asset_count
  FROM assessmentsapp__table__unified_asset_mdata_pg
  WHERE execution_id IN (SELECT latest_execution_id FROM exec_ids)
    AND platform_account_id = {{platformAccountId}}
  GROUP BY execution_id
  HAVING COUNT(DISTINCT asset_key) > 0

  UNION ALL

  -- Fallback: management systems with NO asset_mdata — use findings
  SELECT execution_id, COUNT(DISTINCT asset_key) AS asset_count
  FROM assessmentsapp__table__unified_config_assmt_finding_pg
  WHERE execution_id IN (
    SELECT e.latest_execution_id FROM exec_ids e
    WHERE NOT EXISTS (
      SELECT 1 FROM assessmentsapp__table__unified_asset_mdata_pg m
      WHERE m.execution_id = e.latest_execution_id
        AND m.platform_account_id = {{platformAccountId}}
    )
  )
    AND platform_account_id = {{platformAccountId}}
  GROUP BY execution_id
) combined
```

**Why SUM not COUNT(DISTINCT)?** `COUNT(DISTINCT asset_key)` across both
management systems would collapse the same physical device if it appears
in both. `SUM(per_execution_count)` correctly totals each management
system's unique asset count independently.

---

## 4. Resolver: `ruleEvaluations`

Returns per-rule counts and metadata. Has **three code paths** based on
input parameters.

### Path A — `assetKey` provided (per-asset rule view)

Triggered when `assetKey` is in the request. Returns one row per rule that
evaluated the asset. Two sub-modes via `isRuleAggregation`:

- `false` (default): returns individual rule result + findingId per rule
- `true`: aggregates all rules → returns total counts across all rules for
  the asset

Core dedup subquery (same for both sub-modes):

```sql
FROM (
  SELECT DISTINCT ON (management_system_id, asset_key, source_id)
    source_id, asset_key, management_system_id, finding_type, detected_at, finding_id
  FROM assessmentsapp__table__unified_config_assmt_finding_pg
  WHERE execution_id IN (SELECT latest_execution_id FROM exec_ids)
    AND platform_account_id = {{platformAccountId}}
    AND asset_key = {{assetKey}}
  ORDER BY management_system_id, asset_key, source_id DESC
) d
```

### Path B — `evaluationStatus` filter or count-based sort

Triggered when `evaluationStatus` is provided, or when sorting by count
columns (`assetsEvaluatedCount`, `didNotPassCount`, etc.). Uses a
`deduped` CTE + `counts` CTE:

```sql
, deduped AS (
  SELECT DISTINCT ON (management_system_id, asset_key, source_id)
    source_id, asset_key, management_system_id, finding_type, detected_at
  FROM assessmentsapp__table__unified_config_assmt_finding_pg
  WHERE execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
    AND platform_account_id = {{platformAccountId}}
    -- optional ruleId filter --
  ORDER BY management_system_id, asset_key, source_id DESC
)
, counts AS (
  SELECT
    d.source_id,
    COUNT(*)                                                         AS "assetsEvaluatedCount",
    COUNT(CASE WHEN d.finding_type = 'finding'                THEN 1 END) AS "didNotPassCount",
    COUNT(CASE WHEN d.finding_type = 'ok'                     THEN 1 END) AS "passedCount",
    COUNT(CASE WHEN d.finding_type IN ('missing_info','error') THEN 1 END) AS "inconclusiveCount",
    COUNT(CASE WHEN d.finding_type = 'not_applicable'         THEN 1 END) AS "notApplicableCount",
    MAX(d.detected_at) AS "lastEvaluatedAt"
  FROM deduped d GROUP BY d.source_id
  -- optional HAVING for evaluationStatus filter --
)
```

**Why `COUNT(*)` after `DISTINCT ON`?** After the dedup, each row is a
unique `(management_system_id, asset_key, source_id)` triplet. `COUNT(*)`
equals `COUNT(DISTINCT (management_system_id, asset_key))`. Using
`COUNT(DISTINCT asset_key)` at this point would incorrectly collapse a
device that exists in two management systems.

### Path C — Default paginated (no assetKey, no evaluationStatus)

Uses `paginated_rules` CTE first (applies sorting + LIMIT), then `deduped`
scoped to those rules, then `counts`:

```sql
, paginated_rules AS (
  SELECT source_id, MAX(rule_name) AS rule_name, MAX(severity) AS severity, ...
  FROM assessmentsapp__table__unified_rule_mdata_pg rm
  WHERE rm.execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
    AND rm.platform_account_id = {{platformAccountId}}
    AND EXISTS (
      SELECT 1 FROM findings f
      WHERE f.source_id = rm.source_id
        AND f.execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
        AND f.platform_account_id = {{platformAccountId}}
    )
    -- severity/category/search filters applied here on rule_mdata --
  GROUP BY rm.source_id
  ORDER BY <sort expression>
  OFFSET {{offset}} LIMIT {{limit}}
)
, deduped AS (
  SELECT DISTINCT ON (management_system_id, asset_key, source_id) ...
  FROM findings
  WHERE execution_id IN (SELECT latest_execution_id FROM exec_ids)
    AND platform_account_id = {{platformAccountId}}
    AND source_id IN (SELECT source_id FROM paginated_rules)  -- key: scope to page
  ORDER BY management_system_id, asset_key, source_id DESC
)
```

**Key optimization:** `source_id IN (SELECT source_id FROM paginated_rules)`
scopes the dedup to only the rules on the current page, avoiding a
full-table scan for every count request.

---

## 5. Resolver: `findings`

Returns the paginated list of findings with full asset detail.

### Old approach — problems

The old code applied `OFFSET/LIMIT` to the deduplicated findings rows
**before** JOINing CVI. If some deduplicated rows had DISCONNECTED assets,
the final page was shorter than requested (pagination bug). It also used
the wrong dedup key `(platform_account_id, asset_key, source_id)`.

### New approach — findings-first pagination

**Stage 1:** Compute the page of `(management_system_id, asset_key)` pairs
using `EXISTS(CVI CONNECTED + all asset attribute filters)`. Apply
`OFFSET/LIMIT` here — this is the smallest scoped set:

```sql
, findings_assets AS (
  SELECT DISTINCT f.management_system_id, f.asset_key
  FROM assessmentsapp__table__unified_config_assmt_finding_pg f
  WHERE f.execution_id IN (SELECT latest_execution_id FROM exec_ids)
    AND f.platform_account_id = {{platformAccountId}}
    AND f.source_id = {{ruleId}}            -- if ruleId provided
    AND f.finding_id = {{findingId}}        -- if findingId provided
    AND f.finding_type IN {{result}}        -- if result filter
    AND EXISTS (
      SELECT 1 FROM assets__table__cvi_assets_view a
      WHERE a.id = f.asset_key
        AND a.management_system_id = f.management_system_id
        AND a.platform_account_id = f.platform_account_id
        AND a.connectivity = 'CONNECTED'
        AND a.product_type IN {{productType}}   -- if asset filters
        -- ... all other asset attribute filters inside EXISTS
    )
  ORDER BY f.management_system_id, f.asset_key
  OFFSET {{offset}} LIMIT {{limit}}
)
```

**Stage 2:** Fetch one finding row per `(mgmt × asset × rule)` for the
page's assets only:

```sql
, finding_details AS (
  SELECT DISTINCT ON (management_system_id, asset_key, source_id) *
  FROM assessmentsapp__table__unified_config_assmt_finding_pg
  WHERE execution_id IN (SELECT latest_execution_id FROM exec_ids)
    AND platform_account_id = {{platformAccountId}}
    AND source_id = {{ruleId}}             -- if ruleId provided
    AND finding_id = {{findingId}}         -- if findingId provided
    AND (management_system_id, asset_key)
        IN (SELECT management_system_id, asset_key FROM findings_assets)
  ORDER BY management_system_id, asset_key, source_id, detected_at DESC
)
```

**Stage 3:** JOIN to CVI and PAC for display columns (only for the page's
N assets — not the full table):

```sql
SELECT [all columns]
FROM finding_details f
JOIN assets__table__cvi_assets_view a
  ON f.asset_key = a.id
 AND f.management_system_id = a.management_system_id
 AND a.platform_account_id = f.platform_account_id
 AND a.connectivity = 'CONNECTED'
LEFT JOIN pin__table__asset_criticality_results_pg pac
  ON pac.asset_key = f.asset_key
 AND pac.mgmt_system_id = f.management_system_id
 AND pac.platform_account_id = f.platform_account_id
```

### Performance

On a 95k-asset account (APSE2 NPRD):

| Approach | Timing |
|---|---|
| Old (full JOIN then paginate) | ~1810 ms |
| New (findings-first pagination) | ~13 ms |

**139× improvement** because Stage 1 returns at most `LIMIT` rows (e.g.,
10) before any detail fetch.

### findingId must be applied in both stages

Apply `finding_id = {{findingId}}` in **both** `findings_assets` (to scope
the page) **and** `finding_details` (to scope the detail fetch). Applying
it only in a final WHERE after the JOIN can return wrong results when
combined with OFFSET.

---

## 6. Resolver: `findingsCount`

Returns the total count for pagination. Must stay consistent with
`findings`.

### Single unified path

```sql
WITH exec_ids AS MATERIALIZED (
  SELECT latest_execution_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = {{platformAccountId}}
)
SELECT COUNT(*) AS totalCount
FROM assessmentsapp__table__unified_config_assmt_finding_pg f
WHERE f.execution_id IN (SELECT latest_execution_id FROM exec_ids)
  AND f.platform_account_id = {{platformAccountId}}
  AND f.source_id = {{ruleId}}          -- if ruleId provided
  AND f.asset_key = {{assetKey}}        -- if assetKey provided
  AND f.finding_id = {{findingId}}      -- if findingId provided
  AND f.finding_type IN {{result}}      -- if result filter
  AND f.severity IN {{severity}}        -- if severity filter
  AND f.hostname ILIKE {{hostname}}     -- if hostname filter
  AND EXISTS (
    SELECT 1 FROM assets__table__cvi_assets_view a
    WHERE a.id = f.asset_key
      AND a.management_system_id = f.management_system_id
      AND a.platform_account_id = f.platform_account_id
      AND a.connectivity = 'CONNECTED'
      AND a.product_type IN {{productType}}  -- all asset filters inside EXISTS
      -- ... remaining asset attribute filters
  )
  AND EXISTS (  -- only when role filter present
    SELECT 1 FROM pin__table__asset_criticality_results_pg pac
    WHERE pac.asset_key = f.asset_key
      AND pac.mgmt_system_id = f.management_system_id
      AND pac.platform_account_id = f.platform_account_id
      AND pac.role IN {{role}}
  )
  AND EXISTS (  -- only when importance filter present
    SELECT 1 FROM pin__table__asset_criticality_results_pg pac
    WHERE pac.asset_key = f.asset_key
      AND pac.mgmt_system_id = f.management_system_id
      AND pac.platform_account_id = f.platform_account_id
      AND pac.importance IN {{importance}}
  )
```

### Why `COUNT(*)` without DISTINCT is correct

The old code used `COUNT(DISTINCT (asset_key, source_id))` which dropped
the `management_system_id` dimension.

After the `exec_ids` CTE returns one execution per management system, and
`source_id` is filtered, no two rows in the result set share the same
`(management_system_id, asset_key, source_id)` triplet. Therefore:

```
COUNT(*) = COUNT(DISTINCT (management_system_id, asset_key))
```

Validated on prod data across 4 accounts and 3 regions — diff was 0 in
all cases.

**PAC as separate EXISTS (not LEFT JOIN):** Using `LEFT JOIN pac` then
filtering `pac.role IN (...)` silently converts the join to an inner join,
blocking results when PAC has no row. Two independent `EXISTS` subqueries
are semantically correct and let the planner short-circuit each filter
independently.

---

## 7. SQL Optimization Principles

### Rule 1 — Always scope exec_ids with MATERIALIZED

```sql
-- Prevents the subquery from being re-evaluated multiple times
WITH exec_ids AS MATERIALIZED (
  SELECT latest_execution_id
  FROM assessmentsapp__table__unified_cust_connector_exec_track_pg
  WHERE platform_account_id = {{platformAccountId}}
)
```

### Rule 2 — EXISTS for filtering, JOIN for column values

```sql
-- Filtering: EXISTS short-circuits at first matching CVI row
AND EXISTS (
  SELECT 1 FROM assets__table__cvi_assets_view a
  WHERE a.id = f.asset_key AND a.management_system_id = f.management_system_id
    AND a.platform_account_id = f.platform_account_id AND a.connectivity = 'CONNECTED'
    AND a.product_type IN {{productType}}  -- all filters inside EXISTS
)

-- Column values: JOIN only for the page's rows (after pagination)
JOIN assets__table__cvi_assets_view a ON ...
```

CVI has 68 indexes all leading with `platform_account_id`. The EXISTS path
can use a nested-loop index scan. A JOIN forces materialising all matching
rows first.

### Rule 3 — Paginate the smallest scoped set first

Never apply `OFFSET/LIMIT` to rows that will later be filtered by a JOIN.
Apply pagination to the CTE that has already applied all filters, then
JOIN for display columns only for the resulting N rows.

### Rule 4 — Dedup key must include management_system_id

```sql
-- After this, COUNT(*) is safe to use
SELECT DISTINCT ON (management_system_id, asset_key, source_id) ...
ORDER BY management_system_id, asset_key, source_id DESC  -- must match DISTINCT ON prefix
```

### Rule 5 — Scope count CTEs to paginated rules

In Path C (`paginated_rules`), scope the `deduped` and `counts` CTEs:

```sql
AND source_id IN (SELECT source_id FROM paginated_rules)
```

Without this, counts scan the full findings table for every page request.

### Rule 6 — `IN (...)` vs `= ANY(ARRAY(...))`

Both are valid and produce the same plan. The convention in this resolver
suite is `IN (SELECT ... FROM exec_ids)` for the main WHERE clause and
`= ANY(ARRAY(SELECT ... FROM exec_ids))` for some Path B/C variants.
Either form is fine; don't mix them in a single query for readability.

---

## 8. Resolver Validation Test Suite

Use this 8-query pattern to validate any BAQS resolver change on a target
account before committing.

**Required inputs:** `PAID`, `RULE_ID`, `ASSET_KEY`, `FINDING_ID` from a
known account in the target region.

### Q1 — assessmentExecutions

Validates the UNION ALL hybrid and that `assetsCount` is non-null.

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id,updated_at FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>' ORDER BY updated_at DESC) SELECT (SELECT COUNT(DISTINCT rm.source_id) FROM assessmentsapp__table__unified_rule_mdata_pg rm WHERE rm.platform_account_id='<PAID>' AND EXISTS(SELECT 1 FROM assessmentsapp__table__unified_config_assmt_finding_pg f WHERE f.execution_id IN(SELECT latest_execution_id FROM exec_ids) AND f.platform_account_id='<PAID>' AND f.source_id=rm.source_id LIMIT 1)) AS "rulesCount",(SELECT MAX(updated_at) FROM exec_ids) AS "executedAt",(SELECT SUM(asset_count) FROM(SELECT execution_id,COUNT(DISTINCT asset_key) AS asset_count FROM assessmentsapp__table__unified_asset_mdata_pg WHERE execution_id IN(SELECT latest_execution_id FROM exec_ids) AND platform_account_id='<PAID>' GROUP BY execution_id HAVING COUNT(DISTINCT asset_key)>0 UNION ALL SELECT execution_id,COUNT(DISTINCT asset_key) AS asset_count FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id IN(SELECT e.latest_execution_id FROM exec_ids e WHERE NOT EXISTS(SELECT 1 FROM assessmentsapp__table__unified_asset_mdata_pg m WHERE m.execution_id=e.latest_execution_id AND m.platform_account_id='<PAID>')) AND platform_account_id='<PAID>' GROUP BY execution_id) combined) AS "assetsCount"
```

### Q2 — ruleEvaluations Path A1 (assetKey, per-rule)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>') SELECT d.source_id AS "ruleId",MAX(d.finding_type) AS "result",MAX(d.finding_id) AS "findingId",MAX(cat.rule_name) AS "ruleName",MAX(d.detected_at) AS "lastEvaluatedAt",MAX(cat.severity) AS severity FROM(SELECT DISTINCT ON(management_system_id,asset_key,source_id) source_id,asset_key,management_system_id,finding_type,detected_at,finding_id FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id IN(SELECT latest_execution_id FROM exec_ids) AND platform_account_id='<PAID>' AND asset_key='<ASSET_KEY>' ORDER BY management_system_id,asset_key,source_id DESC) d LEFT JOIN(SELECT DISTINCT ON(source_id) source_id,rule_name,severity FROM assessmentsapp__table__unified_rule_mdata_pg WHERE execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND platform_account_id='<PAID>' ORDER BY source_id) cat ON cat.source_id=d.source_id GROUP BY d.source_id ORDER BY CASE LOWER(MAX(cat.severity)) WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 WHEN 'low' THEN 2 WHEN 'information' THEN 1 ELSE 0 END DESC LIMIT 10
```

### Q3 — ruleEvaluations Path A2 (assetKey, aggregated)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>') SELECT MAX(d.source_id) AS "ruleId",COUNT(DISTINCT d.source_id) AS "assetsEvaluatedCount",COUNT(DISTINCT CASE WHEN d.finding_type='finding' THEN d.source_id END) AS "didNotPassCount",COUNT(DISTINCT CASE WHEN d.finding_type='ok' THEN d.source_id END) AS "passedCount",COUNT(DISTINCT CASE WHEN d.finding_type IN('missing_info','error') THEN d.source_id END) AS "inconclusiveCount",COUNT(DISTINCT CASE WHEN d.finding_type='not_applicable' THEN d.source_id END) AS "notApplicableCount",MAX(d.detected_at) AS "lastEvaluatedAt" FROM(SELECT DISTINCT ON(management_system_id,asset_key,source_id) source_id,asset_key,management_system_id,finding_type,detected_at,finding_id FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id IN(SELECT latest_execution_id FROM exec_ids) AND platform_account_id='<PAID>' AND asset_key='<ASSET_KEY>' ORDER BY management_system_id,asset_key,source_id DESC) d LEFT JOIN(SELECT DISTINCT ON(source_id) source_id,rule_name,severity FROM assessmentsapp__table__unified_rule_mdata_pg WHERE execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND platform_account_id='<PAID>' ORDER BY source_id) cat ON cat.source_id=d.source_id GROUP BY d.asset_key
```

### Q4 — ruleEvaluations Path B (evaluationStatus=finding, ruleId scoped)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>'),deduped AS(SELECT DISTINCT ON(management_system_id,asset_key,source_id) source_id,asset_key,management_system_id,finding_type,detected_at FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND platform_account_id='<PAID>' AND source_id='<RULE_ID>' ORDER BY management_system_id,asset_key,source_id DESC),counts AS(SELECT d.source_id,COUNT(*) AS "assetsEvaluatedCount",COUNT(CASE WHEN d.finding_type='finding' THEN 1 END) AS "didNotPassCount",COUNT(CASE WHEN d.finding_type='ok' THEN 1 END) AS "passedCount",COUNT(CASE WHEN d.finding_type IN('missing_info','error') THEN 1 END) AS "inconclusiveCount",COUNT(CASE WHEN d.finding_type='not_applicable' THEN 1 END) AS "notApplicableCount",MAX(d.detected_at) AS "lastEvaluatedAt" FROM deduped d GROUP BY d.source_id HAVING COUNT(CASE WHEN d.finding_type='finding' THEN 1 END)>0) SELECT c.source_id AS "ruleId",c."assetsEvaluatedCount",c."didNotPassCount",c."passedCount",c."inconclusiveCount",c."notApplicableCount",cat.rule_name AS "ruleName",cat.severity,c."lastEvaluatedAt" FROM counts c LEFT JOIN(SELECT DISTINCT ON(source_id) source_id,rule_name,severity FROM assessmentsapp__table__unified_rule_mdata_pg WHERE execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND platform_account_id='<PAID>' ORDER BY source_id) cat ON cat.source_id=c.source_id ORDER BY c."assetsEvaluatedCount" DESC LIMIT 10
```

### Q5 — ruleEvaluations Path C (paginated_rules, ruleId scoped)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>'),paginated_rules AS(SELECT source_id,MAX(rule_name) AS rule_name,MAX(severity) AS severity FROM assessmentsapp__table__unified_rule_mdata_pg rm WHERE rm.execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND rm.platform_account_id='<PAID>' AND rm.source_id='<RULE_ID>' AND EXISTS(SELECT 1 FROM assessmentsapp__table__unified_config_assmt_finding_pg f WHERE f.source_id=rm.source_id AND f.execution_id=ANY(ARRAY(SELECT latest_execution_id FROM exec_ids)) AND f.platform_account_id='<PAID>') GROUP BY rm.source_id ORDER BY CASE LOWER(MAX(severity)) WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 WHEN 'low' THEN 2 WHEN 'information' THEN 1 ELSE 0 END DESC LIMIT 10),deduped AS(SELECT DISTINCT ON(management_system_id,asset_key,source_id) source_id,asset_key,management_system_id,finding_type,detected_at FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id IN(SELECT latest_execution_id FROM exec_ids) AND platform_account_id='<PAID>' AND source_id IN(SELECT source_id FROM paginated_rules) ORDER BY management_system_id,asset_key,source_id DESC),counts AS(SELECT d.source_id,COUNT(*) AS "assetsEvaluatedCount",COUNT(CASE WHEN d.finding_type='finding' THEN 1 END) AS "didNotPassCount",COUNT(CASE WHEN d.finding_type='ok' THEN 1 END) AS "passedCount",COUNT(CASE WHEN d.finding_type IN('missing_info','error') THEN 1 END) AS "inconclusiveCount",COUNT(CASE WHEN d.finding_type='not_applicable' THEN 1 END) AS "notApplicableCount",MAX(d.detected_at) AS "lastEvaluatedAt" FROM deduped d GROUP BY d.source_id) SELECT c.source_id AS "ruleId",c."assetsEvaluatedCount",c."didNotPassCount",c."passedCount",c."inconclusiveCount",c."notApplicableCount",r.rule_name AS "ruleName",r.severity,c."lastEvaluatedAt" FROM counts c JOIN paginated_rules r ON r.source_id=c.source_id ORDER BY CASE LOWER(r.severity) WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 WHEN 'low' THEN 2 WHEN 'information' THEN 1 ELSE 0 END DESC
```

### Q6 — findings Combo 1 (ruleId, LIMIT 10)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>'),findings_assets AS(SELECT DISTINCT f.management_system_id,f.asset_key FROM assessmentsapp__table__unified_config_assmt_finding_pg f WHERE f.execution_id IN(SELECT latest_execution_id FROM exec_ids) AND f.platform_account_id='<PAID>' AND f.source_id='<RULE_ID>' AND EXISTS(SELECT 1 FROM assets__table__cvi_assets_view a WHERE a.id=f.asset_key AND a.management_system_id=f.management_system_id AND a.platform_account_id=f.platform_account_id AND a.connectivity='CONNECTED') ORDER BY f.management_system_id,f.asset_key LIMIT 10),finding_details AS(SELECT DISTINCT ON(management_system_id,asset_key,source_id) * FROM assessmentsapp__table__unified_config_assmt_finding_pg WHERE execution_id IN(SELECT latest_execution_id FROM exec_ids) AND platform_account_id='<PAID>' AND source_id='<RULE_ID>' AND(management_system_id,asset_key)IN(SELECT management_system_id,asset_key FROM findings_assets) ORDER BY management_system_id,asset_key,source_id,detected_at DESC) SELECT f.finding_id AS "findingId",f.source_id AS "ruleId",f.asset_key AS "assetKey",f.finding_type AS result,f.hostname,a.ip_address AS "ipAddress",f.detected_at AS "lastEvaluated" FROM finding_details f JOIN assets__table__cvi_assets_view a ON f.asset_key=a.id AND f.management_system_id=a.management_system_id AND a.platform_account_id=f.platform_account_id AND a.connectivity='CONNECTED' LEFT JOIN pin__table__asset_criticality_results_pg pac ON pac.asset_key=f.asset_key AND pac.mgmt_system_id=f.management_system_id AND pac.platform_account_id=f.platform_account_id WHERE a.platform_account_id='<PAID>'
```

### Q7 — findings Combo 2 (findingId)

Same as Q6 but replace `f.source_id='<RULE_ID>'` with `f.finding_id='<FINDING_ID>'` in both CTEs.

### Q8 — findingsCount (ruleId)

```sql
WITH exec_ids AS MATERIALIZED(SELECT latest_execution_id FROM assessmentsapp__table__unified_cust_connector_exec_track_pg WHERE platform_account_id='<PAID>') SELECT COUNT(*) AS "totalCount" FROM assessmentsapp__table__unified_config_assmt_finding_pg f WHERE f.execution_id IN(SELECT latest_execution_id FROM exec_ids) AND f.platform_account_id='<PAID>' AND f.source_id='<RULE_ID>' AND EXISTS(SELECT 1 FROM assets__table__cvi_assets_view a WHERE a.id=f.asset_key AND a.management_system_id=f.management_system_id AND a.platform_account_id=f.platform_account_id AND a.connectivity='CONNECTED')
```

### Validation checks

After running Q1–Q8, apply these checks:

| Check | Query | Pass condition | Fail means |
|---|---|---|---|
| V1 | Q1 vs Q4/Q5 | `assetsCount >= assetsEvaluatedCount` | assetsCount < assetsEvaluated → multi-mgmt asset counted twice |
| V2 | Q4/Q5 vs Q8 | `assetsEvaluatedCount == findingsCount` | Gap → some evaluated assets are DISCONNECTED in CVI or stale exec_track rows present |
| V3 | All | All timings < 2000 ms | SLA violation |
| V4 | Q4 vs Q5 | Same `assetsEvaluatedCount` | Inconsistency between Path B and Path C |

**V2 gap interpretation:**

```
gap = assetsEvaluatedCount − findingsCount
```

- `gap == 0`: All evaluated assets are CONNECTED in CVI ✅
- `gap > 0, caused by stale exec_track`: Old mgmt system rows inflate dedup count.
  Confirm with: `SELECT management_system_id, updated_at FROM exec_track WHERE platform_account_id = ?`
  then check if the stale mgmt ID has 0 CVI matches.
- `gap > 0, genuine disconnects`: Assets were evaluated but their device is
  currently DISCONNECTED in CVI. Expected in NPRD; investigate in prod.

---

## 9. Quick Reference — Key Table Joins

```sql
-- findings → CVI (always use mgmt_id in ON clause for index efficiency)
JOIN assets__table__cvi_assets_view a
  ON f.asset_key = a.id
 AND f.management_system_id = a.management_system_id
 AND a.platform_account_id = f.platform_account_id  -- enables CVI's platform_account_id index
 AND a.connectivity = 'CONNECTED'

-- findings → PAC (left join — not all assets have criticality data)
LEFT JOIN pin__table__asset_criticality_results_pg pac
  ON pac.asset_key = f.asset_key
 AND pac.mgmt_system_id = f.management_system_id     -- note: mgmt_system_id not management_system_id
 AND pac.platform_account_id = f.platform_account_id

-- findings → rule metadata (one row per rule, pick latest)
LEFT JOIN (
  SELECT DISTINCT ON (source_id) source_id, rule_name, severity, technology, os_type, ...
  FROM assessmentsapp__table__unified_rule_mdata_pg
  WHERE execution_id = ANY(ARRAY(SELECT latest_execution_id FROM exec_ids))
    AND platform_account_id = {{platformAccountId}}
  ORDER BY source_id
) cat ON cat.source_id = f.source_id
```

**PAC column name difference:** `pin__table__asset_criticality_results_pg`
uses `mgmt_system_id` (not `management_system_id`). Always verify against
the schema when joining.
