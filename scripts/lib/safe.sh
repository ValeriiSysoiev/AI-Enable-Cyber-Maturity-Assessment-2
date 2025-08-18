#!/bin/bash
# Safe Bash Library - Bounded utilities to prevent infinite loops and provide clear logging
# Usage: source this file to get access to retry, require_http, and bounded_wait functions

set -euo pipefail

# Colors for logging
SAFE_RED='\033[0;31m'
SAFE_GREEN='\033[0;32m'
SAFE_YELLOW='\033[1;33m'
SAFE_BLUE='\033[0;34m'
SAFE_NC='\033[0m'

# Retry utility with exponential backoff and bounded attempts
# Usage: retry N S command...
# N: max attempts, S: initial delay seconds
retry() {
    local max_attempts=$1
    local initial_delay=$2
    shift 2
    local command=("$@")
    local attempt=1
    local delay=$initial_delay

    # Validate inputs
    if [[ ! "$max_attempts" =~ ^[0-9]+$ ]] || [ "$max_attempts" -lt 1 ] || [ "$max_attempts" -gt 10 ]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} retry: max_attempts must be 1-10, got: $max_attempts" >&2
        return 1
    fi
    
    if [[ ! "$initial_delay" =~ ^[0-9]+$ ]] || [ "$initial_delay" -lt 1 ] || [ "$initial_delay" -gt 60 ]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} retry: initial_delay must be 1-60 seconds, got: $initial_delay" >&2
        return 1
    fi

    echo -e "${SAFE_BLUE}ℹ${SAFE_NC} retry: attempting command with max_attempts=$max_attempts, delay=$initial_delay" >&2
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${SAFE_BLUE}ℹ${SAFE_NC} retry: attempt $attempt/$max_attempts: ${command[*]}" >&2
        
        if "${command[@]}"; then
            echo -e "${SAFE_GREEN}✓${SAFE_NC} retry: command succeeded on attempt $attempt" >&2
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${SAFE_RED}✗${SAFE_NC} retry: command failed after $max_attempts attempts" >&2
            return 1
        fi
        
        echo -e "${SAFE_YELLOW}⚠${SAFE_NC} retry: attempt $attempt failed, retrying in ${delay}s..." >&2
        sleep $delay
        delay=$((delay * 2))
        # Cap exponential backoff at 120 seconds
        [ $delay -gt 120 ] && delay=120
        ((attempt++))
    done
}

# HTTP requirement checker with bounded timeout and correlation ID verification
# Usage: require_http CODE URL [AUTH]
# CODE: expected HTTP status, URL: endpoint to check, AUTH: optional bearer token
require_http() {
    local expected_code="$1"
    local url="$2"
    local auth_token="${3:-}"
    
    # Validate inputs
    if [[ ! "$expected_code" =~ ^[0-9]{3}$ ]]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} require_http: expected_code must be 3-digit HTTP code, got: $expected_code" >&2
        return 1
    fi
    
    if [[ ! "$url" =~ ^https?:// ]]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} require_http: url must start with http:// or https://, got: $url" >&2
        return 1
    fi
    
    echo -e "${SAFE_BLUE}ℹ${SAFE_NC} require_http: checking $url (expect $expected_code)" >&2
    
    # Create temporary files for headers and body
    local temp_headers temp_body
    temp_headers=$(mktemp)
    temp_body=$(mktemp)
    
    # Build curl command with bounded timeout
    local curl_cmd=(curl --max-time 10 -s -w '%{http_code}' -D "$temp_headers" -o "$temp_body")
    
    # Add auth header if provided
    if [ -n "$auth_token" ]; then
        curl_cmd+=(-H "Authorization: Bearer $auth_token")
    fi
    
    curl_cmd+=("$url")
    
    # Execute curl and capture status code
    local actual_code
    actual_code=$("${curl_cmd[@]}" 2>/dev/null || echo "000")
    
    # Extract correlation ID from headers
    local corr_id
    corr_id=$(grep -i "x-correlation-id" "$temp_headers" 2>/dev/null | cut -d: -f2 | tr -d ' \r\n' || echo "")
    
    # Cleanup temp files
    rm -f "$temp_headers" "$temp_body"
    
    # Print correlation ID if found
    if [ -n "$corr_id" ]; then
        echo -e "${SAFE_GREEN}✓${SAFE_NC} require_http: corr-id=$corr_id" >&2
    else
        echo -e "${SAFE_YELLOW}⚠${SAFE_NC} require_http: no X-Correlation-ID header found" >&2
    fi
    
    # Check status code match
    if [ "$actual_code" = "$expected_code" ]; then
        echo -e "${SAFE_GREEN}✓${SAFE_NC} require_http: got expected $expected_code from $url" >&2
        return 0
    else
        echo -e "${SAFE_RED}✗${SAFE_NC} require_http: expected $expected_code but got $actual_code from $url" >&2
        return 1
    fi
}

# Bounded wait utility that polls a command until it succeeds or timeout
# Usage: bounded_wait MAX_SEC 'command to check'
# MAX_SEC: maximum seconds to wait, cmd: command to execute and check
bounded_wait() {
    local max_seconds="$1"
    local check_command="$2"
    
    # Validate inputs
    if [[ ! "$max_seconds" =~ ^[0-9]+$ ]] || [ "$max_seconds" -lt 5 ] || [ "$max_seconds" -gt 300 ]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} bounded_wait: max_seconds must be 5-300, got: $max_seconds" >&2
        return 1
    fi
    
    if [ -z "$check_command" ]; then
        echo -e "${SAFE_RED}✗${SAFE_NC} bounded_wait: check_command cannot be empty" >&2
        return 1
    fi
    
    echo -e "${SAFE_BLUE}ℹ${SAFE_NC} bounded_wait: polling '$check_command' for max ${max_seconds}s" >&2
    
    local start_time end_time elapsed
    start_time=$(date +%s)
    end_time=$((start_time + max_seconds))
    
    local attempt=1
    while true; do
        local current_time
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        echo -e "${SAFE_BLUE}ℹ${SAFE_NC} bounded_wait: attempt $attempt (${elapsed}s elapsed): $check_command" >&2
        
        # Execute the check command
        if eval "$check_command" >/dev/null 2>&1; then
            echo -e "${SAFE_GREEN}✓${SAFE_NC} bounded_wait: command succeeded after ${elapsed}s ($attempt attempts)" >&2
            return 0
        fi
        
        # Check if we've exceeded the timeout
        if [ "$current_time" -ge "$end_time" ]; then
            echo -e "${SAFE_RED}✗${SAFE_NC} bounded_wait: timeout after ${max_seconds}s ($attempt attempts)" >&2
            return 1
        fi
        
        echo -e "${SAFE_YELLOW}⚠${SAFE_NC} bounded_wait: attempt $attempt failed, waiting 5s..." >&2
        sleep 5
        ((attempt++))
    done
}

# Export functions for use in other scripts
export -f retry require_http bounded_wait