#!/usr/bin/env bash
set -euo pipefail
RG="${RG:-rg-aaa-demo}"
API="api-aaa-demo"
API_URL="https://$(az containerapp show -g "$RG" -n "$API" --query properties.configuration.ingress.fqdn -o tsv)"
echo "GET $API_URL/health"
curl -s "$API_URL/health" || true
