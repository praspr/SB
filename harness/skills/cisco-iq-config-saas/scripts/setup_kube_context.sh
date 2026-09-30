#!/usr/bin/env bash
# Bootstrap team-standard kubeconfig aliases for Config SaaS.
#
# This script is intentionally lightweight: it ONLY creates / refreshes the
# canonical kubeconfig context aliases (cx-dev-usw2, cx-nprd-<region>,
# cx-prd-<region>) so that the rest of this skill's helpers
# (run_postgres_query.sh, run_iceberg_query.sh, local_apisix_setup.sh) can
# look them up by name on any teammate's laptop.
#
# It does NOT:
#   * start a port-forward
#   * require sudo
#   * touch /etc/hosts
#   * stay in the foreground
#
# Use local_apisix_setup.sh when you also need the APISIX tunnel (Iceberg).
# Postgres-only workflows do not need an APISIX tunnel.
#
# Usage:
#   bash setup_kube_context.sh                  # interactive
#   bash setup_kube_context.sh dev
#   bash setup_kube_context.sh nprd usw2
#   bash setup_kube_context.sh prod apse2
#   bash setup_kube_context.sh --all            # bootstrap every standard alias

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT=""
REGION=""
ALL_TARGETS=0

print_usage() {
    cat <<'USAGE'
Usage:
  bash setup_kube_context.sh                  (prompts for env, then region)
  bash setup_kube_context.sh dev
  bash setup_kube_context.sh nprd usw2
  bash setup_kube_context.sh nprd apse2
  bash setup_kube_context.sh nprd euc1
  bash setup_kube_context.sh prod usw2
  bash setup_kube_context.sh prod apse2
  bash setup_kube_context.sh prod euc1
  bash setup_kube_context.sh --all

Creates / refreshes the team-standard kubeconfig context alias:
  dev               -> cx-dev-usw2
  nprd <region>     -> cx-nprd-<region>
  prod <region>     -> cx-prd-<region>   (note: 'cx-prd-', not 'cx-prod-')

After this runs, the run_postgres_query.sh / run_iceberg_query.sh helpers
and local_apisix_setup.sh can all resolve targets by env + region.
USAGE
}

parse_args() {
    case "${1:-}" in
        ""|-h|--help)
            if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
                print_usage
                exit 0
            fi
            ;;
        --all)
            ALL_TARGETS=1
            return 0
            ;;
        dev|nprd|prod)
            ENVIRONMENT="$1"
            REGION="${2:-}"
            return 0
            ;;
        *)
            printf "${RED}Error: invalid environment '%s'. Use dev, nprd, or prod.${NC}\n" "$1" >&2
            print_usage >&2
            exit 1
            ;;
    esac
}

prompt_environment() {
    if [[ -n "$ENVIRONMENT" ]]; then
        return 0
    fi
    printf "${BLUE}Select target environment:${NC}\n" >&2
    printf "  1) dev\n  2) nprd\n  3) prod\n" >&2
    local choice
    read -r -p "Enter choice [dev/nprd/prod]: " choice
    case "$choice" in
        1|dev)  ENVIRONMENT="dev" ;;
        2|nprd) ENVIRONMENT="nprd" ;;
        3|prod) ENVIRONMENT="prod" ;;
        *)
            printf "${RED}Error: invalid environment '%s'.${NC}\n" "$choice" >&2
            exit 1
            ;;
    esac
}

prompt_region() {
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        REGION="usw2"
        return 0
    fi
    if [[ -n "$REGION" ]]; then
        return 0
    fi
    local env_display
    env_display="$(printf '%s' "$ENVIRONMENT" | tr '[:lower:]' '[:upper:]')"
    printf "${BLUE}Select %s region:${NC}\n" "$env_display" >&2
    printf "  1) usw2\n  2) apse2\n  3) euc1\n" >&2
    local choice
    read -r -p "Enter choice [usw2/apse2/euc1]: " choice
    case "$choice" in
        1|usw2)  REGION="usw2" ;;
        2|apse2) REGION="apse2" ;;
        3|euc1)  REGION="euc1" ;;
        *)
            printf "${RED}Error: invalid region '%s'.${NC}\n" "$choice" >&2
            exit 1
            ;;
    esac
}

# Echo CLUSTER_NAME ALIAS REGION AWS_PROFILE ROLE_ARN on one line.
# Single source of truth for all targets. Keep in lockstep with
# local_apisix_setup.sh -> configure_environment().
target_spec() {
    local env="$1"
    local region="$2"
    case "$env" in
        dev)
            case "$region" in
                usw2) printf 'cx-usw2-dev01-eks-01 cx-dev-usw2 us-west-2 cx-platform-dev-admin arn:aws:iam::361769598815:role/AWS-CXP-PlatformEng-Admin\n' ;;
                *)    printf "${RED}Error: dev only supports usw2 (got '%s').${NC}\n" "$region" >&2; return 1 ;;
            esac
            ;;
        nprd)
            case "$region" in
                usw2)  printf 'cx-usw2-nprd01-eks-01 cx-nprd-usw2 us-west-2 cx-platform-nprd-admin arn:aws:iam::713881804551:role/AWS-CXP-PlatformEng-Admin\n' ;;
                apse2) printf 'cx-apse2-nprd01-eks-01 cx-nprd-apse2 ap-southeast-2 cx-platform-nprd-admin arn:aws:iam::713881804551:role/AWS-CXP-PlatformEng-Admin\n' ;;
                euc1)  printf 'cx-euc1-nprd01-eks-01 cx-nprd-euc1 eu-central-1 cx-platform-nprd-admin arn:aws:iam::713881804551:role/AWS-CXP-PlatformEng-Admin\n' ;;
                *)     printf "${RED}Error: invalid nprd region '%s' (use usw2/apse2/euc1).${NC}\n" "$region" >&2; return 1 ;;
            esac
            ;;
        prod)
            # Note: cx-platform-prod-admin is the master-account profile that
            # chains into the workload account (047719623103) via the role ARN
            # below. cx-platform-prod-readonly alone does NOT have direct EKS
            # permissions on prod. Mirrors local_apisix_setup.sh exactly.
            case "$region" in
                usw2)  printf 'cx-usw2-prod01-eks-01 cx-prd-usw2 us-west-2 cx-platform-prod-admin arn:aws:iam::047719623103:role/AWS-CXP-PlatformEng-Admin\n' ;;
                apse2) printf 'cx-apse2-prod01-eks-01 cx-prd-apse2 ap-southeast-2 cx-platform-prod-admin arn:aws:iam::047719623103:role/AWS-CXP-PlatformEng-Admin\n' ;;
                euc1)  printf 'cx-euc1-prod01-eks-01 cx-prd-euc1 eu-central-1 cx-platform-prod-admin arn:aws:iam::047719623103:role/AWS-CXP-PlatformEng-Admin\n' ;;
                *)     printf "${RED}Error: invalid prod region '%s' (use usw2/apse2/euc1).${NC}\n" "$region" >&2; return 1 ;;
            esac
            ;;
        *)
            printf "${RED}Error: invalid environment '%s'.${NC}\n" "$env" >&2
            return 1
            ;;
    esac
}

alias_already_works() {
    local alias="$1"
    kubectl --context "$alias" cluster-info >/dev/null 2>&1
}

aws_identity_valid() {
    local profile="$1"
    command -v aws >/dev/null 2>&1 || return 1
    aws sts get-caller-identity --profile "$profile" >/dev/null 2>&1
}

duo_sso_refresh() {
    if ! command -v duo-sso >/dev/null 2>&1; then
        printf "${YELLOW}Warning: 'duo-sso' not on PATH. Skipping SSO refresh.${NC}\n" >&2
        return 0
    fi
    printf "${BLUE}Running duo-sso to refresh AWS credentials...${NC}\n" >&2
    if ! duo-sso; then
        printf "${RED}duo-sso failed.${NC}\n" >&2
        return 1
    fi
}

bootstrap_one() {
    local env="$1"
    local region="$2"

    local spec
    if ! spec="$(target_spec "$env" "$region")"; then
        return 1
    fi

    # shellcheck disable=SC2034  # ROLE_ARN used by aws eks update-kubeconfig args
    local CLUSTER_NAME ALIAS EKS_REGION AWS_PROFILE ROLE_ARN
    read -r CLUSTER_NAME ALIAS EKS_REGION AWS_PROFILE ROLE_ARN <<< "$spec"

    printf "${BLUE}---- %s / %s ----${NC}\n" "$env" "$region"
    printf "${BLUE}Target alias: ${ALIAS}  (cluster: ${CLUSTER_NAME}, region: ${EKS_REGION})${NC}\n"

    if alias_already_works "$ALIAS"; then
        printf "${GREEN}Alias '%s' already reaches the cluster. Nothing to do. ✓${NC}\n\n" "$ALIAS"
        return 0
    fi

    if ! aws_identity_valid "$AWS_PROFILE"; then
        printf "${YELLOW}AWS profile '%s' is not currently valid.${NC}\n" "$AWS_PROFILE" >&2
        if ! duo_sso_refresh; then
            return 1
        fi
        if ! aws_identity_valid "$AWS_PROFILE"; then
            printf "${RED}AWS profile '%s' still invalid after duo-sso.${NC}\n" "$AWS_PROFILE" >&2
            printf "${YELLOW}Verify: aws sts get-caller-identity --profile %s${NC}\n" "$AWS_PROFILE" >&2
            return 1
        fi
    fi

    printf "${YELLOW}Writing kubeconfig alias '%s'...${NC}\n" "$ALIAS"
    if ! aws eks update-kubeconfig \
        --name "$CLUSTER_NAME" \
        --region "$EKS_REGION" \
        --profile "$AWS_PROFILE" \
        --assume-role-arn "$ROLE_ARN" \
        --role-arn "$ROLE_ARN" \
        --alias "$ALIAS" >/dev/null; then
        printf "${RED}aws eks update-kubeconfig failed.${NC}\n" >&2
        printf "${YELLOW}Check that '%s' can assume '%s'.${NC}\n" "$AWS_PROFILE" "$ROLE_ARN" >&2
        return 1
    fi

    if ! alias_already_works "$ALIAS"; then
        printf "${RED}Alias '%s' written but cluster-info still fails.${NC}\n" "$ALIAS" >&2
        return 1
    fi

    printf "${GREEN}Alias '%s' is ready. ✓${NC}\n\n" "$ALIAS"
}

main() {
    parse_args "$@"

    if [[ "$ALL_TARGETS" -eq 1 ]]; then
        local rc=0
        for target in "dev usw2" "nprd usw2" "nprd apse2" "nprd euc1" \
                      "prod usw2" "prod apse2" "prod euc1"; do
            # shellcheck disable=SC2086  # word-split intentional
            bootstrap_one $target || rc=1
        done
        exit "$rc"
    fi

    prompt_environment
    prompt_region
    bootstrap_one "$ENVIRONMENT" "$REGION"
}

main "$@"
