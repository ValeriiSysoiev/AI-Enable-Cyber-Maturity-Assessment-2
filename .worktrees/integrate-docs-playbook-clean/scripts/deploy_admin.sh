#!/usr/bin/env bash
set -euo pipefail

# ---------- Config ----------
# Load from environment variables with defaults where appropriate
SUBSCRIPTION="${SUBSCRIPTION:-}"
RG="${RG:-}"
ACR_NAME="${ACR_NAME:-}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"
STORAGE_CONTAINER="${STORAGE_CONTAINER:-docs}"
APP_API_NAME="${APP_API_NAME:-api-aaa-demo}"
APP_WEB_NAME="${APP_WEB_NAME:-web-aaa-demo}"

# ---------- Validate Required Environment Variables ----------
REQUIRED_VARS=(
    "SUBSCRIPTION:Azure subscription ID"
    "RG:Resource group name"
    "ACR_NAME:Azure Container Registry name"
    "STORAGE_ACCOUNT:Storage account name"
)

MISSING_VARS=()
for var_spec in "${REQUIRED_VARS[@]}"; do
    var_name="${var_spec%%:*}"
    var_desc="${var_spec#*:}"
    if [[ -z "${!var_name}" ]]; then
        MISSING_VARS+=("  - $var_name: $var_desc")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    echo "ERROR: Required environment variables are missing:"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo ""
    echo "Please set these environment variables and try again."
    exit 1
fi

# Derive ACR_SERVER from ACR_NAME after validation
ACR_SERVER="${ACR_NAME}.azurecr.io"

# ---------- Preconditions ----------
command -v az >/dev/null || { echo "Azure CLI not found"; exit 1; }
command -v docker >/dev/null || { echo "Docker not found"; exit 1; }

# Use repo root as build context regardless of where script is called
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

az account set --subscription "$SUBSCRIPTION"
az extension add --name containerapp -y >/dev/null 2>&1 || az extension update --name containerapp -y >/dev/null 2>&1

# Find ACA environment name in the RG unless provided
ACA_ENV_NAME="${ACA_ENV_NAME:-}"
if [[ -z "${ACA_ENV_NAME}" ]]; then
  ACA_ENV_NAME="$(az containerapp env list -g "$RG" --query '[0].name' -o tsv 2>/dev/null || true)"
fi
if [[ -z "${ACA_ENV_NAME}" || "${ACA_ENV_NAME}" == "null" ]]; then
  echo "No Container Apps environment found in $RG. Set ACA_ENV_NAME env var or create an environment first."
  exit 1
fi

# ---------- ACR admin creds (in-memory only) ----------
az acr update -n "$ACR_NAME" --admin-enabled true >/dev/null
ACR_USER="$(az acr credential show -n "$ACR_NAME" --query "username" -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)"

echo "Logging into ACR $ACR_SERVER as $ACR_USER"
echo "$ACR_PASS" | docker login "$ACR_SERVER" -u "$ACR_USER" --password-stdin

# ---------- Build & Push API ----------
echo "Building API image..."
docker buildx build --platform linux/amd64 -t "$ACR_SERVER/ai-maturity-api:0.1.0" -f app/Dockerfile .
docker push "$ACR_SERVER/ai-maturity-api:0.1.0"

# ---------- Create/Update API Container App ----------
if az containerapp show -g "$RG" -n "$APP_API_NAME" >/dev/null 2>&1; then
  echo "Updating Container App: $APP_API_NAME"
  az containerapp update -g "$RG" -n "$APP_API_NAME" \
    --image "$ACR_SERVER/ai-maturity-api:0.1.0" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --set-env-vars USE_MANAGED_IDENTITY=false AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT" AZURE_STORAGE_CONTAINER="$STORAGE_CONTAINER" >/dev/null
else
  echo "Creating Container App: $APP_API_NAME"
  az containerapp create -g "$RG" -n "$APP_API_NAME" \
    --environment "$ACA_ENV_NAME" \
    --image "$ACR_SERVER/ai-maturity-api:0.1.0" \
    --target-port 8000 --ingress external \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --cpu 0.25 --memory 0.5Gi \
    --env-vars USE_MANAGED_IDENTITY=false AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT" AZURE_STORAGE_CONTAINER="$STORAGE_CONTAINER" >/dev/null
fi

API_FQDN="$(az containerapp show -g "$RG" -n "$APP_API_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
API_URL="https://${API_FQDN}"
echo "API_URL=$API_URL"

# ---------- Build & Push Web (bakes API_URL) ----------
echo "Building Web image with NEXT_PUBLIC_API_BASE_URL=$API_URL ..."
docker buildx build --platform linux/amd64 \
  -t "$ACR_SERVER/ai-maturity-web:0.1.1" \
  -f web/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$API_URL" \
  .
docker push "$ACR_SERVER/ai-maturity-web:0.1.1"

# ---------- Create/Update Web Container App ----------
if az containerapp show -g "$RG" -n "$APP_WEB_NAME" >/dev/null 2>&1; then
  echo "Updating Container App: $APP_WEB_NAME"
  az containerapp update -g "$RG" -n "$APP_WEB_NAME" \
    --image "$ACR_SERVER/ai-maturity-web:0.1.1" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" >/dev/null
else
  echo "Creating Container App: $APP_WEB_NAME"
  az containerapp create -g "$RG" -n "$APP_WEB_NAME" \
    --environment "$ACA_ENV_NAME" \
    --image "$ACR_SERVER/ai-maturity-web:0.1.1" \
    --target-port 3000 --ingress external \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --cpu 0.25 --memory 0.5Gi >/dev/null
fi

WEB_FQDN="$(az containerapp show -g "$RG" -n "$APP_WEB_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
WEB_URL="https://${WEB_FQDN}"
echo "WEB_URL=$WEB_URL"

# ---------- Health ----------
echo "Checking API health..."
MAX_RETRIES=3
RETRY_DELAY=2
for i in $(seq 1 $MAX_RETRIES); do
    echo "  Attempt $i of $MAX_RETRIES: $API_URL/health"
    
    # Capture HTTP status code and response
    HTTP_RESPONSE=$(curl --silent --show-error --max-time 10 --write-out "HTTPSTATUS:%{http_code}" "$API_URL/health" 2>&1) || true
    HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed -e 's/HTTPSTATUS:.*//g')
    HTTP_CODE=$(echo "$HTTP_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [[ "$HTTP_CODE" =~ ^2[0-9][0-9]$ ]]; then
        echo "  ✓ Health check passed (HTTP $HTTP_CODE): ${HTTP_BODY:0:100}"
        break
    else
        echo "  ✗ Health check failed (HTTP $HTTP_CODE): ${HTTP_BODY:0:100}"
        if [[ $i -lt $MAX_RETRIES ]]; then
            echo "  Retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
        else
            echo "  ERROR: API health check failed after $MAX_RETRIES attempts"
            echo "  The API may need more time to start or there may be a deployment issue"
            # Not exiting with error to allow deployment to continue
        fi
    fi
done
