#!/usr/bin/env bash
set -euo pipefail
RG="${RG:-rg-aaa-demo}"
API="api-aaa-demo"
WEB="web-aaa-demo"

# Get API FQDN
api_err_file=$(mktemp)
api_fqdn=$(az containerapp show -g "$RG" -n "$API" --query properties.configuration.ingress.fqdn -o tsv --only-show-errors 2>"$api_err_file")
api_exit_code=$?
api_err=$(<"$api_err_file")
rm -f "$api_err_file"

if [[ $api_exit_code -ne 0 ]]; then
    echo "ERROR: Failed to get API container app details (exit code: $api_exit_code)" >&2
    if [[ -n "$api_err" ]]; then
        echo "$api_err" >&2
    fi
    exit 1
fi

if [[ -z "$api_fqdn" || "$api_fqdn" == "null" ]]; then
    echo "ERROR: API container app '$API' not found or has no ingress configured in resource group '$RG'" >&2
    exit 1
fi

# Validate API FQDN looks reasonable
if [[ "$api_fqdn" =~ [[:space:]] ]] || [[ ! "$api_fqdn" =~ \. ]] || [[ ! "$api_fqdn" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "ERROR: API container app '$API' not found or has no ingress configured in resource group '$RG'" >&2
    exit 1
fi

# Get Web FQDN
web_err_file=$(mktemp)
web_fqdn=$(az containerapp show -g "$RG" -n "$WEB" --query properties.configuration.ingress.fqdn -o tsv --only-show-errors 2>"$web_err_file")
web_exit_code=$?
web_err=$(<"$web_err_file")
rm -f "$web_err_file"

if [[ $web_exit_code -ne 0 ]]; then
    echo "ERROR: Failed to get Web container app details (exit code: $web_exit_code)" >&2
    if [[ -n "$web_err" ]]; then
        echo "$web_err" >&2
    fi
    exit 1
fi

if [[ -z "$web_fqdn" || "$web_fqdn" == "null" ]]; then
    echo "ERROR: Web container app '$WEB' not found or has no ingress configured in resource group '$RG'" >&2
    exit 1
fi

# Construct URLs from validated FQDNs
API_URL="https://$api_fqdn"
WEB_URL="https://$web_fqdn"

echo "API_URL=$API_URL"
echo "WEB_URL=$WEB_URL"
