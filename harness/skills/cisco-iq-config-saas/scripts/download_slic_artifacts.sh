#!/usr/bin/env bash
# download_slic_artifacts.sh
#
# Read-only download of the current Config/Security Hardening SLIC artifacts
# (local_store.json, ic_bom.json) for dev/nprd/prod. See
# docs/slic-artifacts.md for the full procedure and safety notes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" <dev|nprd|prod> <dest-dir> [region]

Region defaults to usw2 (the only region this bucket exists in today).
Dest dir is required — this script never picks a destination for you.

Examples:
  bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" dev ./out/dev
  bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" nprd ./out/nprd
  bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" prod ./out/prod

Each object's current version is resolved once via head-object, then both
get-object calls are pinned to those version IDs so the pair is consistent.

If an AWS command fails with an expired-token or SSO credential error, run
duo-sso once and retry. Do not switch profiles.
USAGE
}

ENV="${1:-}"
DEST="${2:-}"
REGION="${3:-usw2}"

if [[ -z "$ENV" || "$ENV" == "-h" || "$ENV" == "--help" ]]; then
  usage
  [[ "$ENV" == "-h" || "$ENV" == "--help" ]] && exit 0
  exit 2
fi

if [[ -z "$DEST" ]]; then
  echo "ERROR: missing <dest-dir>." >&2
  usage >&2
  exit 2
fi

case "$ENV" in
  dev)  PROFILE="platform-dev-admin"  ;;
  nprd) PROFILE="platform-nprd-admin" ;;
  prod) PROFILE="platform-prod-admin" ;;
  *)
    echo "ERROR: unknown env '$ENV' (expected dev|nprd|prod)." >&2
    exit 2
    ;;
esac

case "$REGION" in
  usw2) AWS_REGION="us-west-2" ;;
  apse2) AWS_REGION="ap-southeast-2" ;;
  euc1) AWS_REGION="eu-central-1" ;;
  *)
    echo "ERROR: unknown region '$REGION' (expected usw2|apse2|euc1)." >&2
    exit 2
    ;;
esac

BUCKET="cx-${REGION}-${ENV}01-vc-s3-assessments-configuration"
LOCAL_STORE_KEY="slic-ic-packages/local_store.json"
IC_BOM_KEY="slic-ic-packages/ic_bom.json"

mkdir -p "$DEST"

echo "Resolving current object versions in s3://$BUCKET ..." >&2

LOCAL_STORE_VERSION=$(aws s3api head-object \
  --bucket "$BUCKET" --key "$LOCAL_STORE_KEY" \
  --profile "$PROFILE" --region "$AWS_REGION" \
  --query VersionId --output text)

IC_BOM_VERSION=$(aws s3api head-object \
  --bucket "$BUCKET" --key "$IC_BOM_KEY" \
  --profile "$PROFILE" --region "$AWS_REGION" \
  --query VersionId --output text)

aws s3api get-object \
  --bucket "$BUCKET" --key "$LOCAL_STORE_KEY" \
  --version-id "$LOCAL_STORE_VERSION" \
  --profile "$PROFILE" --region "$AWS_REGION" \
  "$DEST/local_store.json" >/dev/null

aws s3api get-object \
  --bucket "$BUCKET" --key "$IC_BOM_KEY" \
  --version-id "$IC_BOM_VERSION" \
  --profile "$PROFILE" --region "$AWS_REGION" \
  "$DEST/ic_bom.json" >/dev/null

echo "Downloaded to $DEST" >&2
echo "local_store.json version: $LOCAL_STORE_VERSION" >&2
echo "ic_bom.json version:      $IC_BOM_VERSION" >&2
