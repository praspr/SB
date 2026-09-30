#!/usr/bin/env bash
# Local Development Setup Script for Cisco IQ Config SaaS services
# This script sets up the necessary port-forwards and hosts entries for local development

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

HOSTS_ENTRY="127.0.0.1 apisix-gateway.apisix.svc.cluster.local"
NAMESPACE="apisix"
SERVICE="apisix-gateway"

ENVIRONMENT="${1:-}"
# Region argument applies to nprd AND prod (dev is single-region usw2).
REGION="${2:-}"
NPRD_REGION=""
PROD_REGION=""
EKS_CLUSTER_NAME=""
EKS_CLUSTER_ALIAS=""
EKS_REGION=""
EKS_AWS_PROFILE=""
EKS_ROLE_ARN=""
EKS_NAMESPACE="assessments-configuration"

prompt_environment() {
    if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "nprd" && "$ENVIRONMENT" != "prod" ]]; then
        if [[ -n "$ENVIRONMENT" ]]; then
            printf "${RED}Error: Invalid environment '%s'. Use 'dev', 'nprd', or 'prod'.${NC}\n" "$ENVIRONMENT"
            exit 1
        fi

        printf "${BLUE}Select target environment:${NC}\n"
        printf "  1) dev\n"
        printf "  2) nprd\n"
        printf "  3) prod\n"
        read -r -p "Enter choice [dev/nprd/prod]: " ENVIRONMENT

        case "$ENVIRONMENT" in
            1) ENVIRONMENT="dev" ;;
            2) ENVIRONMENT="nprd" ;;
            3) ENVIRONMENT="prod" ;;
            dev|nprd|prod) ;;
            *)
                printf "${RED}Error: Invalid environment '%s'. Use 'dev', 'nprd', or 'prod'.${NC}\n" "$ENVIRONMENT"
                exit 1
                ;;
        esac
    fi

    # Both nprd and prod are multi-region; dev is single-region (usw2 only).
    if [[ ( "$ENVIRONMENT" == "nprd" || "$ENVIRONMENT" == "prod" ) && -z "$REGION" ]]; then
        local env_display
        env_display="$(printf '%s' "$ENVIRONMENT" | tr '[:lower:]' '[:upper:]')"
        printf "${BLUE}Select %s region:${NC}\n" "$env_display"
        printf "  1) usw2\n"
        printf "  2) apse2\n"
        printf "  3) euc1\n"
        read -r -p "Enter choice [usw2/apse2/euc1]: " REGION
    fi

    case "$REGION" in
        "" ) ;;
        1) REGION="usw2" ;;
        2) REGION="apse2" ;;
        3) REGION="euc1" ;;
        usw2|apse2|euc1) ;;
        *)
            printf "${RED}Error: Invalid region '%s'. Use 'usw2', 'apse2', or 'euc1'.${NC}\n" "$REGION"
            exit 1
            ;;
    esac

    case "$ENVIRONMENT" in
        nprd) NPRD_REGION="$REGION" ;;
        prod) PROD_REGION="$REGION" ;;
    esac
}

configure_environment() {
    case "$ENVIRONMENT" in
        dev)
            EKS_CLUSTER_NAME="cx-usw2-dev01-eks-01"
            EKS_CLUSTER_ALIAS="cx-dev-usw2"
            EKS_REGION="us-west-2"
            EKS_AWS_PROFILE="cx-platform-dev-admin"
            EKS_ROLE_ARN="arn:aws:iam::361769598815:role/AWS-CXP-PlatformEng-Admin"
            ;;
        nprd)
            case "$NPRD_REGION" in
                usw2)
                    EKS_CLUSTER_NAME="cx-usw2-nprd01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-nprd-usw2"
                    EKS_REGION="us-west-2"
                    ;;
                apse2)
                    EKS_CLUSTER_NAME="cx-apse2-nprd01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-nprd-apse2"
                    EKS_REGION="ap-southeast-2"
                    ;;
                euc1)
                    EKS_CLUSTER_NAME="cx-euc1-nprd01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-nprd-euc1"
                    EKS_REGION="eu-central-1"
                    ;;
                *)
                    printf "${RED}Error: Invalid NPRD region '%s'. Use 'usw2', 'apse2', or 'euc1'.${NC}\n" "$NPRD_REGION"
                    exit 1
                    ;;
            esac
            EKS_AWS_PROFILE="cx-platform-nprd-admin"
            EKS_ROLE_ARN="arn:aws:iam::713881804551:role/AWS-CXP-PlatformEng-Admin"
            ;;
        prod)
            case "$PROD_REGION" in
                usw2)
                    EKS_CLUSTER_NAME="cx-usw2-prod01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-prd-usw2"
                    EKS_REGION="us-west-2"
                    ;;
                apse2)
                    EKS_CLUSTER_NAME="cx-apse2-prod01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-prd-apse2"
                    EKS_REGION="ap-southeast-2"
                    ;;
                euc1)
                    EKS_CLUSTER_NAME="cx-euc1-prod01-eks-01"
                    EKS_CLUSTER_ALIAS="cx-prd-euc1"
                    EKS_REGION="eu-central-1"
                    ;;
                *)
                    printf "${RED}Error: Invalid PROD region '%s'. Use 'usw2', 'apse2', or 'euc1'.${NC}\n" "$PROD_REGION"
                    exit 1
                    ;;
            esac
            # cx-platform-prod-admin is a master-account profile that chains
            # into the workload account (047719623103) via the role ARN below
            # — same pattern as nprd. The master profile alone (account
            # 905418369215) does NOT have direct EKS permissions on prod.
            EKS_AWS_PROFILE="cx-platform-prod-admin"
            EKS_ROLE_ARN="arn:aws:iam::047719623103:role/AWS-CXP-PlatformEng-Admin"
            ;;
        *)
            printf "${RED}Error: Invalid environment '%s'. Use 'dev', 'nprd', or 'prod'.${NC}\n" "$ENVIRONMENT"
            exit 1
            ;;
    esac
}

print_header() {
    printf "${BLUE}\n"
    printf "╔═══════════════════════════════════════════════════════════╗\n"
    case "$ENVIRONMENT" in
        nprd)
            printf "║   Config SaaS NPRD - Local APISIX Setup                    ║\n"
            ;;
        prod)
            printf "║   Config SaaS PROD - Local APISIX Setup (READ-ONLY)        ║\n"
            ;;
        *)
            printf "║   Config SaaS - Local Development Setup                    ║\n"
            ;;
    esac
    printf "╚═══════════════════════════════════════════════════════════╝\n"
    printf "${NC}\n"

    if [[ "$ENVIRONMENT" == "prod" ]]; then
        printf "${YELLOW}WARNING: You are connecting to a PRODUCTION cluster.${NC}\n"
        printf "${YELLOW}  - Treat any data accessed via this port-forward as customer-sensitive.${NC}\n"
        printf "${YELLOW}  - SELECT-only by policy. Do not run mutating SQL through Trino.${NC}\n\n"
    fi
}

# If kube context already works (same idea as run_postgres_query.sh: assume creds ok until proven otherwise),
# skip Duo SSO and aws eks update-kubeconfig — avoids interactive auth on every run.
kubectl_cluster_already_reachable() {
    kubectl config use-context "$EKS_CLUSTER_ALIAS" &>/dev/null || return 1
    kubectl config set-context --current --namespace="$EKS_NAMESPACE" &>/dev/null || true
    kubectl cluster-info &>/dev/null
}

# Same check as postgres-k8s-query-testing skill: avoid Duo when AWS session is still valid.
aws_identity_valid() {
    command -v aws &>/dev/null || return 1
    aws sts get-caller-identity --profile "$EKS_AWS_PROFILE" &>/dev/null
}

duo_sso_auth() {
    printf "${BLUE}[1/5] Authenticating with Duo SSO...${NC}\n"

    # Check if duo-sso command exists
    if ! command -v duo-sso &>/dev/null; then
        printf "${YELLOW}Warning: duo-sso command not found. Skipping SSO auth.${NC}\n"
        printf "${YELLOW}If you need SSO, install duo-sso and run it manually.${NC}\n"
        return 0
    fi

    # Run duo-sso authentication
    printf "${YELLOW}Running duo-sso authentication...${NC}\n"
    if duo-sso; then
        printf "${GREEN}Duo SSO authentication successful ✓${NC}\n"
    else
        printf "${RED}Duo SSO authentication failed.${NC}\n"
        printf "${YELLOW}Try running 'duo-sso' manually and then re-run this script.${NC}\n"
        exit 1
    fi
}

check_kubectl() {
    printf "${BLUE}Configuring Kubernetes connection...${NC}\n"

    if [[ -n "$EKS_REGION" && -n "$EKS_AWS_PROFILE" && -n "$EKS_ROLE_ARN" ]]; then
        printf "${YELLOW}Updating kubeconfig for EKS cluster ${EKS_CLUSTER_NAME} (alias: ${EKS_CLUSTER_ALIAS})...${NC}\n"
        if ! aws eks update-kubeconfig \
            --name "$EKS_CLUSTER_NAME" \
            --region "$EKS_REGION" \
            --profile "$EKS_AWS_PROFILE" \
            --assume-role-arn "$EKS_ROLE_ARN" \
            --role-arn "$EKS_ROLE_ARN" \
            --alias "$EKS_CLUSTER_ALIAS" 2>&1; then
            printf "${RED}Error: Failed to update kubeconfig for EKS cluster.${NC}\n"
            printf "${YELLOW}Check that AWS profile '${EKS_AWS_PROFILE}' can assume '${EKS_ROLE_ARN}'.${NC}\n"
            exit 1
        fi
    fi

    kubectl config use-context "$EKS_CLUSTER_ALIAS" &>/dev/null
    kubectl config set-context --current --namespace="$EKS_NAMESPACE" &>/dev/null

    if ! kubectl cluster-info &>/dev/null; then
        case "$ENVIRONMENT" in
            nprd|prod)
                printf "${RED}Error: Cannot connect to Kubernetes cluster '${EKS_CLUSTER_ALIAS}'.${NC}\n"
                printf "Please ensure your kube context is valid and try again.\n"
                ;;
            *)
                printf "${RED}Error: Cannot connect to Kubernetes cluster.${NC}\n"
                printf "Please ensure your AWS credentials are valid and try again.\n"
                ;;
        esac
        exit 1
    fi
    printf "${GREEN}Connected to: ${EKS_CLUSTER_ALIAS} (namespace: ${EKS_NAMESPACE}) ✓${NC}\n"
}

setup_hosts() {
    printf "${BLUE}Setting up hosts file...${NC}\n"
    if grep -q "apisix-gateway.apisix.svc.cluster.local" /etc/hosts; then
        printf "${GREEN}Hosts entry already exists ✓${NC}\n"
    else
        printf "${YELLOW}Adding hosts entry (requires sudo)...${NC}\n"
        echo "$HOSTS_ENTRY" | sudo tee -a /etc/hosts > /dev/null
        printf "${GREEN}Hosts entry added ✓${NC}\n"
    fi
}

cleanup_port_forwards() {
    printf "${BLUE}Cleaning up existing port-forwards...${NC}\n"
    sudo pkill -f "kubectl port-forward.*apisix-gateway" 2>/dev/null || true
    sleep 1
    printf "${GREEN}Cleanup complete ✓${NC}\n"
}

show_instructions() {
    printf "\n"
    printf "${GREEN}════════════════════════════════════════════════════════════${NC}\n"
    case "$ENVIRONMENT" in
        nprd) printf "${GREEN}  NPRD Setup Ready!${NC}\n" ;;
        prod) printf "${GREEN}  PROD Setup Ready! (READ-ONLY)${NC}\n" ;;
        *)    printf "${GREEN}  Setup Ready!${NC}\n" ;;
    esac
    printf "${GREEN}════════════════════════════════════════════════════════════${NC}\n"
    printf "\n"
    printf "  ${BLUE}Configuration:${NC}\n"
    case "$ENVIRONMENT" in
        nprd|prod)
            printf "    - Region: ${REGION}\n"
            printf "    - Context: ${EKS_CLUSTER_ALIAS}\n"
            printf "    - Hosts entry: apisix-gateway.apisix.svc.cluster.local -> 127.0.0.1\n"
            printf "    - Port 80  -> $SERVICE:80 (HTTP)\n"
            printf "    - Port 443 -> $SERVICE:443 (HTTPS)\n"
            ;;
        *)
            printf "    - Hosts entry: apisix-gateway.apisix.svc.cluster.local -> 127.0.0.1\n"
            printf "    - Port 80  -> $SERVICE:9080 (HTTP)\n"
            printf "    - Port 443 -> $SERVICE:9443 (HTTPS)\n"
            ;;
    esac
    printf "\n"
    printf "  ${BLUE}Next Steps:${NC}\n"
    printf "    1. Keep this terminal open (port-forward runs here)\n"
    case "$ENVIRONMENT" in
        nprd|prod)
            printf "    2. In another terminal, run your read-only Trino queries against:\n"
            printf "       ${YELLOW}https://apisix-gateway.apisix.svc.cluster.local/trino${NC} (per .env TRINO_*)\n"
            ;;
        *)
            printf "    2. Open a new terminal and run: ${YELLOW}./scripts/start_agent_ui.sh${NC}\n"
            ;;
    esac
    printf "\n"
    printf "  ${YELLOW}Press Ctrl+C to stop port-forward.${NC}\n"
    printf "\n"
}

start_port_forward() {
    printf "${BLUE}Starting port-forward (requires sudo for ports 80/443)...${NC}\n"
    printf "${YELLOW}Enter your password if prompted:${NC}\n\n"

    case "$ENVIRONMENT" in
        nprd|prod)
            sudo kubectl --context "$EKS_CLUSTER_ALIAS" port-forward service/$SERVICE 80:80 443:443 -n $NAMESPACE
            ;;
        *)
            sudo kubectl port-forward services/$SERVICE 80:80 443:443 -n $NAMESPACE
            ;;
    esac
}

# Trap to handle cleanup on exit
cleanup_on_exit() {
    printf "\n${YELLOW}Stopping port-forward...${NC}\n"
    sudo pkill -f "kubectl port-forward.*apisix-gateway" 2>/dev/null || true
    printf "${GREEN}Port-forward stopped.${NC}\n"
}

trap cleanup_on_exit EXIT INT TERM

# Main execution
prompt_environment
configure_environment
print_header

if kubectl_cluster_already_reachable; then
    printf "${GREEN}Kubernetes already reachable - skipping Duo SSO and kubeconfig refresh ✓${NC}\n"
    printf "${GREEN}Using context: ${EKS_CLUSTER_ALIAS} (namespace: ${EKS_NAMESPACE}) ✓${NC}\n"
elif aws_identity_valid; then
    printf "${GREEN}AWS credentials active (profile: ${EKS_AWS_PROFILE}) - skipping Duo SSO ✓${NC}\n"
    check_kubectl
else
    duo_sso_auth
    if ! aws_identity_valid; then
        printf "${RED}Error: AWS profile '${EKS_AWS_PROFILE}' is not valid after SSO.${NC}\n"
        printf "${YELLOW}Verify with: aws sts get-caller-identity --profile ${EKS_AWS_PROFILE}${NC}\n"
        exit 1
    fi
    check_kubectl
fi

setup_hosts
cleanup_port_forwards
show_instructions
start_port_forward
