#!/usr/bin/env bash
set -euo pipefail

# ---------- Config ----------
SUBSCRIPTION="10233675-d493-4a97-9c81-4001e353a7bb"
RG="rg-aaa-demo"
ACR_NAME="acraaademo9lyu53"
ACR_SERVER="${ACR_NAME}.azurecr.io"
ACA_ENV_NAME="${ACA_ENV_NAME:-}"     # allow override via env
APP_API_NAME="${APP_API_NAME:-api-aaa-demo}"
APP_WEB_NAME="${APP_WEB_NAME:-web-aaa-demo}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-staaademo6jshgh}"
STORAGE_CONTAINER="${STORAGE_CONTAINER:-docs}"

# ---------- Preconditions ----------
command -v az >/dev/null || { echo "Azure CLI not found"; exit 1; }
command -v docker >/dev/null || { echo "Docker not found"; exit 1; }

az account set --subscription "$SUBSCRIPTION"
az extension add --name containerapp -y >/dev/null 2>&1 || az extension update --name containerapp -y >/dev/null 2>&1

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
echo "API health:"
curl -s "$API_URL/health" || true
