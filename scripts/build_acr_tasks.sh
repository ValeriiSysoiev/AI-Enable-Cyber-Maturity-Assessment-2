#!/usr/bin/env bash
set -euo pipefail

SUBSCRIPTION="${SUBSCRIPTION:-10233675-d493-4a97-9c81-4001e353a7bb}"
RG="${RG:-rg-aaa-demo}"
ACR="${ACR:-acraaademo9lyu53}"

# Image tags
API_IMAGE_TAG="${API_IMAGE_TAG:-ai-maturity-api:0.1.0}"
WEB_IMAGE_TAG="${WEB_IMAGE_TAG:-ai-maturity-web:0.1.2}"

# Go to repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

az account set --subscription "$SUBSCRIPTION"

# Build API (context: app/, Dockerfile: app/Dockerfile)
az acr build -r "$ACR" -t "$API_IMAGE_TAG" -f app/Dockerfile --platform linux/amd64 app

# Build Web (context: web/, Dockerfile: web/Dockerfile), bake API URL
API_URL="${API_URL:-}"
if [ -z "$API_URL" ]; then
  echo "API_URL not set — building web without it. Use deploy_containerapps.sh to discover API URL, then rebuild web if needed."
  az acr build -r "$ACR" -t "$WEB_IMAGE_TAG" -f web/Dockerfile --platform linux/amd64 web
else
  az acr build -r "$ACR" -t "$WEB_IMAGE_TAG" -f web/Dockerfile --build-arg NEXT_PUBLIC_API_BASE_URL="$API_URL" --platform linux/amd64 web
fi
