#!/usr/bin/env bash
# run_iceberg_query.sh
#
# Query UDM Iceberg tables via Amazon Athena directly against the Glue Data
# Catalog — no Trino, no APISIX, no local port-forward, no sudo. Mirrors the
# ergonomics of run_postgres_query.sh.
#
# Auth: plain AWS SSO profile (platform-<env>-admin), the same "assumed
# workload" profile already used for Secrets Manager reads in this skill.
# No secret to fetch, no principal to harvest — auth is refreshed with one
# duo-sso retry on an expired/missing SSO token (see _iceberg_query.py).
#
# Database naming: cx-<region>-<env>01-datafabric-glue-catalog — the Glue
# database is queried directly (via Athena's QueryExecutionContext), so
# table names are unqualified (no iceberg."<schema>". prefix needed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_HELPER="$SCRIPT_DIR/_iceberg_query.py"

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" <env> [region] [SQL]
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" <env> [region]            # interactive REPL

Examples:
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" dev "SHOW TABLES"
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" nprd usw2 "SELECT count(*) FROM assetsudm__table__udm_asset"
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod apse2 "SELECT * FROM assetsudm__table__udm_asset LIMIT 5"
  bash "$SKILL_DIR/scripts/run_iceberg_query.sh" prod apse2 --excel out.xlsx "SELECT * FROM ... LIMIT 100"

Required positional:
  <env>     dev | nprd | prod
  [region]  usw2 | apse2 | euc1   (required for nprd and prod; ignored for dev)

Optional flags (anywhere on the command line):
  --database <name>           Override Glue database (default: cx-<region>-<env>01-datafabric-glue-catalog)
  --workgroup <name>           Athena workgroup (default: primary, or ICEBERG_WORKGROUP)
  --output-s3 <s3://...>       Override Athena output bucket (default: Data Fabric's own
                              cx-<region>-<env>01-datafabric-s3-datalakehouse/athena-query-results/;
                              the "primary" workgroup has no default configured so this is required
                              one way or another)
  --json                      Emit results as JSON to stdout.
  --csv  <path>               Also write CSV to <path>.
  --excel, -x <path>          Also write XLSX to <path>.
  --truncate N                Truncate cell display to N chars (default 120; 0 = no truncate).
  --timeout N                  Query timeout in seconds (default 120).
  --repl, -i                   Force interactive REPL even if SQL is given.
  -h, --help                   Show this help.

Optional env overrides:
  ICEBERG_PROFILE, ICEBERG_REGION, ICEBERG_DATABASE, ICEBERG_OUTPUT_S3,
  ICEBERG_WORKGROUP, ICEBERG_QUERY_TIMEOUT, ICEBERG_QUERY_TRUNCATE,
  AUTO_DUO_SSO (set 0 to disable auto duo-sso retry on auth errors)

Pre-reqs:
  None beyond a working AWS SSO session for platform-<env>-admin. If the
  session is stale, this script runs duo-sso once automatically and retries.
USAGE
}

# ---- env/region -> profile / AWS region / database / output bucket ----

profile_for_env() {
  case "$1" in
    dev)  echo "platform-dev-admin" ;;
    nprd) echo "platform-nprd-admin" ;;
    prod) echo "platform-prod-admin" ;;
    *)
      echo "Invalid env '$1'. Use dev, nprd, or prod." >&2
      return 1
      ;;
  esac
}

aws_region_for_region_token() {
  case "$1" in
    usw2)  echo "us-west-2" ;;
    apse2) echo "ap-southeast-2" ;;
    euc1)  echo "eu-central-1" ;;
    *)
      echo "Invalid region '$1'. Use usw2, apse2, or euc1." >&2
      return 1
      ;;
  esac
}

env_label_for_target() {
  case "$1" in
    dev)  echo "dev01" ;;
    nprd) echo "nprd01" ;;
    prod) echo "prod01" ;;
  esac
}

# Same "cx-<region>-<env>01-datafabric-*" naming the Data Fabric team uses
# for the Glue catalog itself — just a different suffix.
database_for_env_region() {
  echo "cx-$2-$(env_label_for_target "$1")-datafabric-glue-catalog"
}

# Verified to exist across dev/nprd/prod x usw2/apse2/euc1 (unlike the
# per-app "*-athena-query-results" / "*-athena-results" buckets, which are
# inconsistently named or missing in some env/region combos). This is the
# Data Fabric team's own datalakehouse bucket — NOT the health-risk-insights
# app's bucket, which is unrelated to Config SaaS / UDM Iceberg data.
output_s3_for_env_region() {
  echo "s3://cx-$2-$(env_label_for_target "$1")-datafabric-s3-datalakehouse/athena-query-results/"
}

# ---- arg parsing --------------------------------------------------------

CLI_ENV=""
CLI_REGION=""
CLI_DATABASE=""
CLI_WORKGROUP=""
CLI_JSON=0
CLI_CSV_PATH=""
CLI_XLSX_PATH=""
CLI_TRUNCATE=""
CLI_TIMEOUT=""
CLI_REPL=0
SQL_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --database)
      CLI_DATABASE="${2:-}"
      shift 2 || { echo "ERROR: --database requires a value" >&2; exit 2; }
      ;;
    --workgroup)
      CLI_WORKGROUP="${2:-}"
      shift 2 || { echo "ERROR: --workgroup requires a value" >&2; exit 2; }
      ;;
    --output-s3)
      ICEBERG_OUTPUT_S3="${2:-}"
      shift 2 || { echo "ERROR: --output-s3 requires an s3:// path" >&2; exit 2; }
      ;;
    --json)
      CLI_JSON=1
      shift
      ;;
    --csv)
      CLI_CSV_PATH="${2:-}"
      shift 2 || { echo "ERROR: --csv requires a path" >&2; exit 2; }
      ;;
    --excel|-x)
      CLI_XLSX_PATH="${2:-}"
      shift 2 || { echo "ERROR: --excel requires a path" >&2; exit 2; }
      ;;
    --truncate)
      CLI_TRUNCATE="${2:-}"
      shift 2 || { echo "ERROR: --truncate requires an integer" >&2; exit 2; }
      ;;
    --timeout)
      CLI_TIMEOUT="${2:-}"
      shift 2 || { echo "ERROR: --timeout requires an integer" >&2; exit 2; }
      ;;
    --repl|-i)
      CLI_REPL=1
      shift
      ;;
    dev|nprd|prod)
      if [[ -z "$CLI_ENV" ]]; then
        CLI_ENV="$1"
        shift
      else
        SQL_ARGS+=("$1")
        shift
      fi
      ;;
    usw2|apse2|euc1)
      if [[ -z "$CLI_REGION" && ( "$CLI_ENV" == "nprd" || "$CLI_ENV" == "prod" ) ]]; then
        CLI_REGION="$1"
        shift
      else
        SQL_ARGS+=("$1")
        shift
      fi
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        SQL_ARGS+=("$1")
        shift
      done
      ;;
    -*)
      echo "ERROR: unknown flag: $1" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
    *)
      SQL_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$CLI_ENV" ]]; then
  echo "ERROR: missing <env>. Use dev, nprd, or prod." >&2
  echo "Run bash \"\$SKILL_DIR/scripts/run_iceberg_query.sh\" --help for usage." >&2
  exit 2
fi

if [[ "$CLI_ENV" == "nprd" || "$CLI_ENV" == "prod" ]]; then
  if [[ -z "$CLI_REGION" ]]; then
    echo "ERROR: ${CLI_ENV} requires a region (usw2 | apse2 | euc1)." >&2
    exit 2
  fi
else
  CLI_REGION="usw2"
fi

ICEBERG_PROFILE="$(profile_for_env "$CLI_ENV")" || exit 1
ICEBERG_REGION="$(aws_region_for_region_token "$CLI_REGION")" || exit 1
ICEBERG_DATABASE="${CLI_DATABASE:-$(database_for_env_region "$CLI_ENV" "$CLI_REGION")}"
ICEBERG_WORKGROUP="${CLI_WORKGROUP:-${ICEBERG_WORKGROUP:-primary}}"
# The "primary" workgroup has no default result configuration in this
# account, so Athena requires an explicit OutputLocation. Default to the
# Data Fabric team's own datalakehouse bucket (verified present across all
# nine env/region combos) rather than an app-specific bucket unrelated to
# Config SaaS. Override with --output-s3 / ICEBERG_OUTPUT_S3 if needed.
ICEBERG_OUTPUT_S3="${ICEBERG_OUTPUT_S3:-$(output_s3_for_env_region "$CLI_ENV" "$CLI_REGION")}"

export ICEBERG_PROFILE ICEBERG_REGION ICEBERG_DATABASE ICEBERG_WORKGROUP ICEBERG_OUTPUT_S3

cat >&2 <<EOF
Athena query target:
  env / region : ${CLI_ENV} / ${CLI_REGION}
  profile      : ${ICEBERG_PROFILE}
  aws region   : ${ICEBERG_REGION}
  database     : ${ICEBERG_DATABASE}
  output       : ${ICEBERG_OUTPUT_S3}
EOF

# ---- assemble SQL string -----------------------------------------------

SQL_STR=""
if [[ ${#SQL_ARGS[@]} -gt 0 ]]; then
  SQL_STR="${SQL_ARGS[*]}"
elif [[ -p /dev/stdin || ( ! -t 0 && -f /dev/stdin ) ]]; then
  echo "Reading SQL from stdin..." >&2
  SQL_STR="$(cat)"
fi

# ---- invoke python helper ----------------------------------------------

PY_ARGS=()
if (( CLI_REPL )) || [[ -z "${SQL_STR//[[:space:]]/}" ]]; then
  PY_ARGS+=("--repl")
else
  PY_ARGS+=("--sql" "$SQL_STR")
fi
if (( CLI_JSON )); then
  PY_ARGS+=("--json")
fi
if [[ -n "$CLI_CSV_PATH" ]]; then
  PY_ARGS+=("--csv-path" "$CLI_CSV_PATH")
fi
if [[ -n "$CLI_XLSX_PATH" ]]; then
  PY_ARGS+=("--xlsx-path" "$CLI_XLSX_PATH")
fi
if [[ -n "$CLI_TRUNCATE" ]]; then
  PY_ARGS+=("--truncate" "$CLI_TRUNCATE")
fi
if [[ -n "$CLI_TIMEOUT" ]]; then
  PY_ARGS+=("--timeout" "$CLI_TIMEOUT")
fi

exec python3 "$PYTHON_HELPER" "${PY_ARGS[@]}"
