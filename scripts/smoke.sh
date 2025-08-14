#!/usr/bin/env bash
set -euo pipefail
RG="${RG:-rg-aaa-demo}"
API="api-aaa-demo"

# Get API FQDN
az_err_file=$(mktemp)
FQDN=$(az containerapp show -g "$RG" -n "$API" --query properties.configuration.ingress.fqdn -o tsv --only-show-errors 2>"$az_err_file")
az_exit_code=$?
az_err=$(<"$az_err_file")
rm -f "$az_err_file"

if [[ $az_exit_code -ne 0 ]]; then
    echo "ERROR: Failed to get API container app details (exit code: $az_exit_code)" >&2
    if [[ -n "$az_err" ]]; then
        echo "$az_err" >&2
    fi
    exit 1
fi

if [[ -z "$FQDN" || "$FQDN" == "null" ]]; then
    echo "ERROR: API container app '$API' not found or has no ingress configured in resource group '$RG'" >&2
    exit 1
fi

# Validate FQDN looks reasonable (contains at least one dot)
if [[ ! "$FQDN" =~ \. ]]; then
    echo "ERROR: Invalid FQDN received: '$FQDN'" >&2
    exit 1
fi

# Construct URL from validated FQDN
API_URL="https://$FQDN"

echo "GET $API_URL/health"

# Make the health check request with explicit error handling
curl_err_file=$(mktemp)
HTTP_RESPONSE=$(curl --silent --show-error --max-time 10 --write-out "\nHTTPSTATUS:%{http_code}" "$API_URL/health" 2>"$curl_err_file")
curl_exit_code=$?
curl_err=$(<"$curl_err_file")
rm -f "$curl_err_file"

if [[ $curl_exit_code -ne 0 ]]; then
    echo "ERROR: curl failed with exit code $curl_exit_code" >&2
    if [[ -n "$curl_err" ]]; then
        echo "Error details: $curl_err" >&2
    fi
    if [[ -n "$HTTP_RESPONSE" ]]; then
        echo "Response: $HTTP_RESPONSE" >&2
    fi
    exit 1
fi

# Extract body and status code
HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')
HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1 | sed -e 's/.*HTTPSTATUS://')

# Check for successful response
if [[ "$HTTP_CODE" =~ ^2[0-9][0-9]$ ]]; then
    echo "Success (HTTP $HTTP_CODE): $HTTP_BODY"
else
    echo "ERROR: Health check failed with HTTP $HTTP_CODE" >&2
    echo "Response: $HTTP_BODY" >&2
    exit 1
fi
