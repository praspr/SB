# Config SaaS Table Registry

Use this registry before writing SQL. Config SaaS Postgres consumption tables
are unversioned `*__table__*` names (for example `assessmentsapp__table__*`,
`assets__table__*`, `pin__table__*`).

## Config SaaS Runtime Tables (SLIC, unversioned)

These unversioned table names are shared by `configbp-ai` and current
`cbp-engine` Helm defaults. The same logical name applies in dev, nprd,
and prod across all three regions unless platform ops announce an
environment-specific override.

| Logical table | `TRINO_TABLE_*` env key | Postgres/Trino table |
| --- | --- | --- |
| assessment | `TRINO_TABLE_ASSESSMENT` | `assessmentsapp__table__unified_assessments_pg` |
| assessment execution | `TRINO_TABLE_EXECUTION` | `assessmentsapp__table__unified_assessments_execution_pg` |
| finding | `TRINO_TABLE_FINDING` | `assessmentsapp__table__unified_config_assmt_finding_pg` |
| insights | `TRINO_TABLE_INSIGHTS` | `assessmentsapp__table__unified_config_assmt_insights_pg` |
| recommendation | `TRINO_TABLE_RECOMMENDATION` | `assessmentsapp__table__unified_config_assmt_recommendation_pg` |
| connector execution tracking | `TRINO_TABLE_EXECUTION_TRACKING` | `assessmentsapp__table__unified_cust_connector_exec_track_pg` |
| expert notifications queue | (not exported via env) | `assessmentsapp__table__unified_config_assmt_expert_notify_q_pg` |
| asset metadata | (not exported via env) | `assessmentsapp__table__unified_asset_mdata_pg` |
| rule metadata | (not exported via env) | `assessmentsapp__table__unified_rule_mdata_pg` |
| asset view (CVI) | `TRINO_TABLE_ASSETS_VIEW` | `assets__table__cvi_assets_view` |
| asset criticality results | `TRINO_TABLE_ASSET_CRITICALITY` | `pin__table__asset_criticality_results_pg` |

## Security Hardening tables (parallel family)

Every BAQS resolver that touches findings or recommendations has two
parallel branches — one for `assessmentCategory = "Configuration"` and
one for `assessmentCategory = "SecurityHardening"`. The SecurityHardening
tables share the same schema as their Config counterparts.

| Logical table | Postgres table |
| --- | --- |
| SecurityHardening finding | `assessmentsapp__table__unified_sec_hrd_assmt_finding_pg` |
| SecurityHardening recommendation | `assessmentsapp__table__unified_sec_hrd_assmt_recommendation_pg` |

These tables use the same join keys (`execution_id`, `asset_key`,
`management_system_id`, `platform_account_id`, `source_id`) as the Config
tables. The `exec_track` and `rule_mdata` tables are shared between both
families.

Expert Insights and asset-scope SQL join the asset tables above via
`TRINO_TABLE_ASSETS_VIEW` and `TRINO_TABLE_ASSET_CRITICALITY`
(`agent/services/expert_insights_trino.py`, `mcp_server/core/trino_config.py`).
Through Trino's Postgres connector the fully qualified form is
`postgresql.public.<table_name>`.

## Legacy Lifecycle Names

Do not use old lifecycle-style `configuration_*_pg_<version>` table names for
Config SaaS runtime SQL unless the user explicitly asks about historical
lifecycle definitions. Current runtime investigation should use the
unversioned `*__table__*` names in the table above.

## UDM Iceberg Tables

`cbp-engine` (`src/cbp_engine/config.py` in `assessment-unified-engine`)
now reads the **unversioned** `assetsudm__table__*` names — not the old
version-pinned `udm_*_1__0__N` names. Both exist live (the unversioned
name is a view/alias over the current version), but use the unversioned
name for SQL so it doesn't need updating on every Data Fabric version
bump. Query via `run_iceberg_query.sh <env> [region] "<sql>"` (Athena
directly against the Glue database, table names unqualified).

| Logical table | Table name |
| --- | --- |
| UDM asset | `assetsudm__table__udm_asset` |
| UDM asset telemetry | `assetsudm__table__udm_asset_telemetry` |
| UDM contract coverage | `assetsudm__table__udm_contract_coverage` |
| UDM software | `assetsudm__table__udm_software` |
| UDM device command | `assetsudm__table__udm_device_command` |
| UDM product | `assetsudm__table__udm_product` |
| UDM HW/EoX bulletins | `assetsudm__table__udm_hweox_bulletins` |

Version-pinned names (e.g. `udm_device_command_1__0__7`) still exist and
are confirmable with `SHOW TABLES` if a specific version is ever needed.

## Update Protocol

When the user supplies updated table information:

1. Update this registry in-place.
2. Use the new table in the current query.
3. Do not update repo `.env`, DBML, Helm values, or lifecycle files unless the
   user explicitly asks for a repo code/config change.
