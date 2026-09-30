# Cisco IQ Config SaaS Reference

This reference captures cross-repo operational facts for the Config SaaS stack.
It intentionally omits credential values, service credential payloads, and raw
secret JSON.

## Repositories

| Repo | Role |
| --- | --- |
| `configbp-ai` | A2A gateway, agent API, MCP server, ConfigBP expert insights and query tooling |
| `cbp-engine` | Producer/worker/packager pipeline for SLIC evaluation and finding persistence |
| `cxp-cbp-etl` | Lifecycle definitions for Data Fabric tables, ETL templates/instances, connectors, IAM, and message topics |

## Environments and Regions

| Env | Regions | Kubernetes contexts |
| --- | --- | --- |
| `dev` | `usw2` | `cx-dev-usw2` |
| `nprd` | `usw2`, `apse2`, `euc1` | `cx-nprd-usw2`, `cx-nprd-apse2`, `cx-nprd-euc1` |
| `prod` | `usw2`, `apse2`, `euc1` | `cx-prd-usw2`, `cx-prd-apse2`, `cx-prd-euc1` |

Primary namespace:

```text
assessments-configuration
```

Supporting namespaces used by helper scripts:

```text
apisix
sre-baseapps
cxp-query-service
```

## Secret Path Conventions

Do not print secret payloads into chat. Confirm with the user before any
dev/nprd write, and do not perform prod writes.

| Service area | Secret path pattern |
| --- | --- |
| ConfigBP AI | `cx/<region-token>/<env>01/configbp-ai/secrets/agent-secrets` |
| cbp-engine / validation-and-compliance | `cx/<region-token>/<env>01/validation-and-compliance/secrets/assessments-configuration-secrets` |
| cxp-cbp-etl lifecycle | `cx/<region-token>/<env>01/lifecycle/secrets/cbp-lifecycle-etl-secrets` |

Region tokens are `usw2`, `apse2`, and `euc1`. AWS regions are `us-west-2`,
`ap-southeast-2`, and `eu-central-1`.

Use assumed workload profiles for Secrets Manager work:

| Env | Profile |
| --- | --- |
| dev | `platform-dev-admin` |
| nprd | `platform-nprd-admin` |
| prod reads | `platform-prod-admin` when available; otherwise treat local prod access as read-only and limited |

## Data Stores

Aurora/Postgres access goes through:

```bash
bash "$SKILL_DIR/scripts/run_postgres_query.sh" <env> [region] "<sql>"
```

Iceberg/UDM access goes through Amazon Athena directly against the Glue
Data Catalog:

```bash
bash "$SKILL_DIR/scripts/run_iceberg_query.sh" <env> [region] "<sql>"
```

Glue database (table names are unqualified within it):

```text
cx-<region-token>-<env>01-datafabric-glue-catalog
```

## High-Level Pipeline

```text
cxp-cbp-etl lifecycle definitions
  -> Data Fabric connector / ETL / message topic
  -> asset ETL notification topic
  -> cbp-engine producer
  -> Aurora assessment + execution rows (engine_status = PENDING, payload = UDM table names)
  -> KEDA PostgreSQL scaler polls execution table, spawns cbp-engine-worker-job
  -> cbp-engine worker claims row (engine_status -> INPROGRESS)
  -> UDM Iceberg command/asset joins
  -> SLIC evaluation
  -> Aurora findings / recommendations / insights
  -> configbp-ai agent and MCP responses
```

## Kafka Topics

| Topic | Producer/consumer usage |
| --- | --- |
| `cvi.datalake.asset.notifications` | External asset upload notifications consumed by cbp-engine producer |
| `assessmentsapp.asset.etl.notification` | ETL completion notifications consumed by cbp-engine |
| `assessments.app.execution.status` | Internal assessment execution status topic used by cbp-engine producer/worker |

## cbp-engine Roles

| Role | Purpose |
| --- | --- |
| `producer` | Consumes asset/ETL notifications, creates assessment/execution rows, publishes internal execution messages |
| `worker` | Consumes execution messages, fetches eligible UDM devices/commands, runs SLIC, writes results |
| `packager` | Refreshes `local_store.json` and `ic_bom.json` artifacts in S3 |

The cbp-engine Helm chart uses `assessments-configuration` as the global
namespace and `validation-and-compliance` secret paths for runtime secrets.

## Safety Rules

- Prod SQL must be `SELECT` only and should include `LIMIT` for exploratory reads.
- Treat customer rows, platform account IDs, command outputs, and findings as sensitive.
- Never copy service credential base64 values from Helm, env files, or Secrets Manager into skill files, logs, or chat.
- Prefer counts, schemas, and redacted summaries over raw row dumps.
