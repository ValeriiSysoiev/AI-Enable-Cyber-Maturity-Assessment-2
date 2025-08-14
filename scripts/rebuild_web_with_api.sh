#!/usr/bin/env bash
set -euo pipefail

SUBSCRIPTION="${SUBSCRIPTION:-10233675-d493-4a97-9c81-4001e353a7bb}"
RG="${RG:-rg-aaa-demo}"
ACR="${ACR:-acraaademo9lyu53}"
ACR_SERVER="${ACR}.azurecr.io"
WEB_APP="${WEB_APP:-web-aaa-demo}"
API_APP="${API_APP:-api-aaa-demo}"

# Generate unique image tag
if [ -n "${WEB_IMAGE_TAG:-}" ]; then
  # Use provided tag if set
  UNIQUE_TAG="$WEB_IMAGE_TAG"
else
  # Generate timestamp-based tag
  UNIQUE_TAG="ai-maturity-web:$(date +%Y%m%d%H%M%S)"
  # Alternatively, use git commit SHA if available
  # if git rev-parse --short HEAD &>/dev/null; then
  #   UNIQUE_TAG="ai-maturity-web:$(git rev-parse --short HEAD)"
  # fi
fi

# Generate revision suffix for Container App
# Azure Container Apps revision suffix rules:
# - Must start with a lowercase letter
# - Can only contain lowercase letters, numbers, and hyphens
# - Cannot contain consecutive hyphens
# - Must end with an alphanumeric character
# - Maximum 64 characters
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
# Prefix with 'r', sanitize, and ensure compliance
REVISION_SUFFIX="r${TIMESTAMP}"
# Remove any non-allowed characters and collapse double dashes
REVISION_SUFFIX=$(echo "$REVISION_SUFFIX" | tr -cd 'a-z0-9-' | sed 's/--*/-/g')
# Trim trailing non-alphanumeric characters
REVISION_SUFFIX=$(echo "$REVISION_SUFFIX" | sed 's/[^a-z0-9]*$//')
# Truncate to 64 characters
REVISION_SUFFIX="${REVISION_SUFFIX:0:64}"

az account set --subscription "$SUBSCRIPTION"

# Check for API URL override via environment variable
# NEXT_PUBLIC_API_BASE_URL takes precedence over Azure Container App FQDN lookup
if [ -n "${NEXT_PUBLIC_API_BASE_URL:-}" ]; then
  echo "Using API URL from NEXT_PUBLIC_API_BASE_URL environment variable"
  API_URL="$NEXT_PUBLIC_API_BASE_URL"
  
  # Normalize URL to ensure it has https:// prefix
  if [[ ! "$API_URL" =~ ^https?:// ]]; then
    API_URL="https://${API_URL}"
  fi
  
  echo "API URL set to: $API_URL"
else
  # Get API FQDN and validate
  echo "Retrieving API FQDN for $API_APP..."
  FQDN_OUTPUT=$(mktemp)
  ERROR_OUTPUT=$(mktemp)

  # Run the command and capture output
  if az containerapp show -g "$RG" -n "$API_APP" --query properties.configuration.ingress.fqdn -o tsv >"$FQDN_OUTPUT" 2>"$ERROR_OUTPUT"; then
    FQDN=$(cat "$FQDN_OUTPUT")
    
    # Check if FQDN is empty or "null"
    if [ -z "$FQDN" ] || [ "$FQDN" = "null" ]; then
      echo "Error: API FQDN is empty or null" >&2
      [ -s "$ERROR_OUTPUT" ] && cat "$ERROR_OUTPUT" >&2
      rm -f "$FQDN_OUTPUT" "$ERROR_OUTPUT"
      exit 1
    fi
  else
    echo "Error: Failed to retrieve API FQDN" >&2
    cat "$ERROR_OUTPUT" >&2
    rm -f "$FQDN_OUTPUT" "$ERROR_OUTPUT"
    exit 1
  fi

  rm -f "$FQDN_OUTPUT" "$ERROR_OUTPUT"
  API_URL="https://${FQDN}"
fi

# Validate the resolved API URL
if [ -z "$API_URL" ]; then
  echo "Error: API_URL is empty after resolution" >&2
  exit 1
fi

echo "Rebuilding web with NEXT_PUBLIC_API_BASE_URL=$API_URL"
echo "Using image tag: $UNIQUE_TAG"

# Build in ACR with baked API_URL
echo "Building image in ACR..."
az acr build -r "$ACR" \
  -t "$UNIQUE_TAG" \
  -f web/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$API_URL" \
  --platform linux/amd64 \
  web

# Optionally push a "latest" tag alongside the unique tag
if [ "${PUSH_LATEST:-false}" = "true" ]; then
  echo "Tagging as latest..."
  # Parse repository name from UNIQUE_TAG (everything before the colon)
  REPO_NAME="${UNIQUE_TAG%%:*}"
  az acr import --name "$ACR" \
    --source "${ACR_SERVER}/${UNIQUE_TAG}" \
    --image "${REPO_NAME}:latest" \
    --force
fi

# Update web app to the new image with revision suffix
echo "Updating container app to use new image with revision: $REVISION_SUFFIX..."
if ! az containerapp update -g "$RG" -n "$WEB_APP" \
  --image "$ACR_SERVER/$UNIQUE_TAG" \
  --revision-suffix "$REVISION_SUFFIX"; then
  echo "Error: Failed to update container app" >&2
  exit 1
fi

echo "Web app successfully updated with new image: $UNIQUE_TAG"
echo "New revision suffix: $REVISION_SUFFIX"
