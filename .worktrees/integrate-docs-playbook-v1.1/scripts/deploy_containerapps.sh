#!/usr/bin/env bash
set -euo pipefail

SUBSCRIPTION="${SUBSCRIPTION:-10233675-d493-4a97-9c81-4001e353a7bb}"
RG="${RG:-rg-aaa-demo}"
ENV="${ENV:-aca-aaa-demo}"
ACR="${ACR:-acraaademo9lyu53}"
ACR_SERVER="${ACR}.azurecr.io"
API_APP="${API_APP:-api-aaa-demo}"
WEB_APP="${WEB_APP:-web-aaa-demo}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-staaademo6jshgh}"
STORAGE_CONTAINER="${STORAGE_CONTAINER:-docs}"

# Image tags
API_IMAGE_TAG="${API_IMAGE_TAG:-ai-maturity-api:0.1.0}"
WEB_IMAGE_TAG="${WEB_IMAGE_TAG:-ai-maturity-web:0.1.2}"

az account set --subscription "$SUBSCRIPTION"
az extension add --name containerapp -y >/dev/null 2>&1 || az extension update --name containerapp -y >/dev/null 2>&1

# Enable ACR admin (temporary) so Container Apps can pull
az acr update -n "$ACR" --admin-enabled true >/dev/null
ACR_USER="$(az acr credential show -n "$ACR" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"

# Create/update API
if az containerapp show -g "$RG" -n "$API_APP" >/dev/null 2>&1; then
  az containerapp update -g "$RG" -n "$API_APP" \
    --image "$ACR_SERVER/$API_IMAGE_TAG" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --set-env-vars USE_MANAGED_IDENTITY=false AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT" AZURE_STORAGE_CONTAINER="$STORAGE_CONTAINER"
else
  az containerapp create -g "$RG" -n "$API_APP" \
    --environment "$ENV" \
    --image "$ACR_SERVER/$API_IMAGE_TAG" \
    --target-port 8000 --ingress external \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --cpu 0.25 --memory 0.5Gi \
    --env-vars USE_MANAGED_IDENTITY=false AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT" AZURE_STORAGE_CONTAINER="$STORAGE_CONTAINER"
fi

API_URL="https://$(az containerapp show -g "$RG" -n "$API_APP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "API_URL=$API_URL"

# Create/update Web; if built without API_URL earlier, this still runs
if az containerapp show -g "$RG" -n "$WEB_APP" >/dev/null 2>&1; then
  az containerapp update -g "$RG" -n "$WEB_APP" \
    --image "$ACR_SERVER/$WEB_IMAGE_TAG" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS"
else
  az containerapp create -g "$RG" -n "$WEB_APP" \
    --environment "$ENV" \
    --image "$ACR_SERVER/$WEB_IMAGE_TAG" \
    --target-port 3000 --ingress external \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --cpu 0.25 --memory 0.5Gi
fi

WEB_URL="https://$(az containerapp show -g "$RG" -n "$WEB_APP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "WEB_URL=$WEB_URL"
