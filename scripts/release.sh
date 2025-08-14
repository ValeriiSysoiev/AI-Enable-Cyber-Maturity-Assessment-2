#!/usr/bin/env bash
set -euo pipefail

# -------- Config (override via env) --------
SUBSCRIPTION="${SUBSCRIPTION:-}"  # optional; if set, we'll switch
RG="${RG:-rg-aaa-demo}"
ACR_NAME="${ACR_NAME:-acraaademo9lyu53}"
ACR_SERVER="${ACR_SERVER:-$ACR_NAME.azurecr.io}"
API_APP="${API_APP:-api-aaa-demo}"
WEB_APP="${WEB_APP:-web-aaa-demo}"
ADMIN_EMAILS="${ADMIN_EMAILS:-va.sysoiev@audit3a.com}"
TAG="${TAG:-v$(date +%Y%m%d%H%M)-$(git rev-parse --short HEAD)}"
NO_COMMIT="${NO_COMMIT:-0}"

need() { command -v "$1" >/dev/null || { echo "Missing $1"; exit 1; }; }
need az; need git; command -v jq >/dev/null || echo "(optional) jq not found – pretty printing JSON will be skipped"

# Ensure repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "==> Release config:"
echo "SUBSCRIPTION=${SUBSCRIPTION:-<unchanged>}"
echo "RG=$RG"
echo "ACR=$ACR_NAME ($ACR_SERVER)"
echo "API_APP=$API_APP"
echo "WEB_APP=$WEB_APP"
echo "ADMIN_EMAILS=$ADMIN_EMAILS"
echo "TAG=$TAG"

# Optional: set subscription
if [ -n "${SUBSCRIPTION}" ]; then
  echo "==> Switching subscription to $SUBSCRIPTION"
  az account set --subscription "$SUBSCRIPTION"
fi

# Pre-flight: ensure RG exists
if ! az group show -n "$RG" >/dev/null 2>&1; then
  echo "ERROR: Resource Group $RG not found."
  exit 1
fi

# Pre-flight: ensure Container Apps extension
az extension add --name containerapp -y >/dev/null 2>&1 || true

# Commit & push (optional)
if [ "$NO_COMMIT" != "1" ]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  echo "==> Committing & pushing on branch $BRANCH"
  git add -A
  git commit -m "release: deploy $TAG" || echo "(no local changes to commit)"
  git push || echo "(push skipped/failed – check credentials if needed)"
fi

# ACR admin + creds
echo "==> Enabling ACR admin"
az acr update -n "$ACR_NAME" --admin-enabled true >/dev/null

echo "==> Fetching ACR creds"
ACR_USER="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"

# Build images in ACR
echo "==> Building API image in ACR: $TAG"
az acr build -r "$ACR_NAME" -t "ai-maturity-api:$TAG" -f app/Dockerfile ./app

echo "==> Building WEB image in ACR: $TAG"
az acr build -r "$ACR_NAME" -t "ai-maturity-web:$TAG" -f web/Dockerfile ./web

# Update API
echo "==> Updating API container app image + env"
az containerapp update -g "$RG" -n "$API_APP" \
  --image "$ACR_SERVER/ai-maturity-api:$TAG" \
  --set-env-vars ADMIN_EMAILS="$ADMIN_EMAILS"

API_FQDN="$(az containerapp show -g "$RG" -n "$API_APP" --query properties.configuration.ingress.fqdn -o tsv)"
API_URL="https://${API_FQDN}"

# Update WEB
echo "==> Updating WEB container app image + env"
az containerapp update -g "$RG" -n "$WEB_APP" \
  --image "$ACR_SERVER/ai-maturity-web:$TAG" \
  --set-env-vars NEXT_PUBLIC_API_BASE="$API_URL"

WEB_FQDN="$(az containerapp show -g "$RG" -n "$WEB_APP" --query properties.configuration.ingress.fqdn -o tsv)"
WEB_URL="https://${WEB_FQDN}"

# Print endpoints
echo "==> Done. Endpoints:"
echo "API_URL=$API_URL"
echo "WEB_URL=$WEB_URL"

# Smoke tests
echo "==> Smoke test: /health and /docs"
set +e
HC="$(curl -s -m 20 "$API_URL/health")"
DOCS_CODE="$(curl -s -o /dev/null -w '%{http_code}' "$API_URL/docs")"
set -e
echo "Health: $HC"
echo "Docs HTTP: $DOCS_CODE"
