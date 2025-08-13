#!/usr/bin/env bash
set -euo pipefail
RG="${RG:-rg-aaa-demo}"
API="api-aaa-demo"
WEB="web-aaa-demo"
API_URL="https://$(az containerapp show -g "$RG" -n "$API" --query properties.configuration.ingress.fqdn -o tsv)"
WEB_URL="https://$(az containerapp show -g "$RG" -n "$WEB" --query properties.configuration.ingress.fqdn -o tsv)"
echo "API_URL=$API_URL"
echo "WEB_URL=$WEB_URL"
