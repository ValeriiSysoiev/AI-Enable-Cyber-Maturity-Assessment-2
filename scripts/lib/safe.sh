#!/bin/bash

# Safe bash utilities for bounded execution
# Provides safe HTTP operations, retries, and timeouts

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
safe_log_info() { echo -e "${BLUE}ℹ${NC} $1" >&2; }
safe_log_success() { echo -e "${GREEN}✓${NC} $1" >&2; }
safe_log_warning() { echo -e "${YELLOW}⚠${NC} $1" >&2; }
safe_log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Safe HTTP request with timeout and correlation ID validation
# Usage: require_http URL [expected_status] [timeout]
require_http() {
    local url="$1"
    local expected_status="${2:-200}"
    local timeout="${3:-10}"
    
    local correlation_id
    correlation_id=$(uuidgen 2>/dev/null || echo "safe-$(date +%s)-$$")
    
    safe_log_info "Testing HTTP endpoint: $url"
    
    # Perform request with timeout and headers check
    local temp_headers temp_body response_code
    temp_headers=$(mktemp)
    temp_body=$(mktemp)
    
    # Cleanup temp files on exit
    trap "rm -f '$temp_headers' '$temp_body'" RETURN
    
    response_code=$(curl -s --max-time "$timeout" \
        -H "X-Correlation-ID: $correlation_id" \
        -D "$temp_headers" \
        -o "$temp_body" \
        -w "%{http_code}" \
        "$url" 2>/dev/null || echo "000")
    
    # Check if correlation ID is present in response
    if grep -qi "X-Correlation-ID" "$temp_headers" 2>/dev/null; then
        safe_log_success "Correlation ID header present in response"
    else
        safe_log_warning "X-Correlation-ID header missing in response from $url"
    fi
    
    # Validate status code
    if [[ "$response_code" == "$expected_status" ]]; then
        safe_log_success "HTTP $url returned expected status $expected_status"
        return 0
    else
        safe_log_error "HTTP $url returned status $response_code, expected $expected_status"
        # Show response body for debugging (truncated)
        if [[ -s "$temp_body" ]]; then
            safe_log_info "Response body (first 200 chars): $(head -c 200 '$temp_body')"
        fi
        return 1
    fi
}

# Retry function with exponential backoff
# Usage: retry max_attempts delay_seconds command [args...]
retry() {
    local max_attempts="$1"
    local delay="$2"
    shift 2
    
    local attempt=1
    
    while (( attempt <= max_attempts )); do
        safe_log_info "Attempt $attempt/$max_attempts: $*"
        
        if "$@"; then
            safe_log_success "Command succeeded on attempt $attempt"
            return 0
        else
            local exit_code=$?
            safe_log_warning "Command failed on attempt $attempt (exit code: $exit_code)"
            
            if (( attempt < max_attempts )); then
                safe_log_info "Waiting ${delay}s before retry..."
                sleep "$delay"
                # Exponential backoff
                delay=$((delay * 2))
                if (( delay > 30 )); then
                    delay=30  # Cap at 30 seconds
                fi
            fi
        fi
        
        ((attempt++))
    done
    
    safe_log_error "Command failed after $max_attempts attempts"
    return 1
}

# Bounded wait with timeout
# Usage: bounded_wait timeout_seconds check_command [check_args...]
bounded_wait() {
    local timeout="$1"
    shift
    
    local start_time end_time elapsed
    start_time=$(date +%s)
    
    safe_log_info "Waiting up to ${timeout}s for condition: $*"
    
    while true; do
        if "$@"; then
            end_time=$(date +%s)
            elapsed=$((end_time - start_time))
            safe_log_success "Condition met after ${elapsed}s"
            return 0
        fi
        
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        
        if (( elapsed >= timeout )); then
            safe_log_error "Timeout after ${elapsed}s waiting for: $*"
            return 1
        fi
        
        safe_log_info "Still waiting... (${elapsed}s/${timeout}s)"
        sleep 2
    done
}

# Safe JSON response validation
# Usage: validate_json_response response_file expected_keys...
validate_json_response() {
    local response_file="$1"
    shift
    local expected_keys=("$@")
    
    if [[ ! -s "$response_file" ]]; then
        safe_log_error "Response file empty or missing"
        return 1
    fi
    
    # Check if valid JSON
    if ! jq empty "$response_file" 2>/dev/null; then
        safe_log_error "Invalid JSON in response"
        safe_log_info "Response content: $(head -c 500 '$response_file')"
        return 1
    fi
    
    # Check for expected keys
    for key in "${expected_keys[@]}"; do
        if jq -e "has(\"$key\")" "$response_file" >/dev/null 2>&1; then
            safe_log_success "JSON contains expected key: $key"
        else
            safe_log_error "JSON missing expected key: $key"
            return 1
        fi
    done
    
    return 0
}

# Safe POST with JSON payload and validation
# Usage: safe_post_json URL payload_file expected_status [timeout]
safe_post_json() {
    local url="$1"
    local payload_file="$2" 
    local expected_status="${3:-200}"
    local timeout="${4:-10}"
    
    local correlation_id
    correlation_id=$(uuidgen 2>/dev/null || echo "safe-$(date +%s)-$$")
    
    safe_log_info "POST to $url with JSON payload"
    
    local temp_headers temp_body response_code
    temp_headers=$(mktemp)
    temp_body=$(mktemp)
    
    trap "rm -f '$temp_headers' '$temp_body'" RETURN
    
    response_code=$(curl -s --max-time "$timeout" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Correlation-ID: $correlation_id" \
        -D "$temp_headers" \
        -d "@$payload_file" \
        -o "$temp_body" \
        -w "%{http_code}" \
        "$url" 2>/dev/null || echo "000")
    
    # Validate correlation ID
    if grep -qi "X-Correlation-ID" "$temp_headers" 2>/dev/null; then
        safe_log_success "Correlation ID header present in response"
    else
        safe_log_warning "X-Correlation-ID header missing in response"
    fi
    
    # Check status
    if [[ "$response_code" == "$expected_status" ]]; then
        safe_log_success "POST $url returned expected status $expected_status"
        # Copy response body to stdout for caller
        cat "$temp_body"
        return 0
    else
        safe_log_error "POST $url returned status $response_code, expected $expected_status"
        if [[ -s "$temp_body" ]]; then
            safe_log_info "Response body: $(head -c 300 '$temp_body')"
        fi
        return 1
    fi
}

# Export functions for use in other scripts
export -f require_http
export -f retry
export -f bounded_wait
export -f validate_json_response
export -f safe_post_json
export -f safe_log_info
export -f safe_log_success
export -f safe_log_warning
export -f safe_log_error