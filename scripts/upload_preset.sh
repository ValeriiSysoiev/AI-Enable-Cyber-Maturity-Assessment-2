#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/upload_preset.sh /path/to/preset.json
PRESET_PATH="${1:-}"
if [ -z "$PRESET_PATH" ] || [ ! -f "$PRESET_PATH" ]; then
  echo "Usage: $0 /path/to/preset.json"
  exit 1
fi

RG="${RG:-rg-aaa-demo}"
API_APP="${API_APP:-api-aaa-demo}"
ADMIN_EMAIL="${ADMIN_EMAIL:-va.sysoiev@audit3a.com}"

API_FQDN="$(az containerapp show -g "$RG" -n "$API_APP" --query properties.configuration.ingress.fqdn -o tsv)"
API_URL="https://${API_FQDN}"

echo "==> Uploading preset to $API_URL/presets/upload"
curl -sS -X POST "$API_URL/presets/upload" \
  -H "X-User-Email: $ADMIN_EMAIL" \
  -H "X-Engagement-ID: bootstrap" \
  -F "file=@${PRESET_PATH}"

echo
echo "==> Listing presets:"
if command -v jq >/dev/null; then
  curl -sS "$API_URL/presets" | jq .
else
  curl -sS "$API_URL/presets"
fi
