#!/bin/bash
# Cursor Safe Runner - Quote-safe harness for CI/CD operations

set -Eeuo pipefail

# Exit handler with status reporting
trap 'code=$?; echo "[cursor_safe_run] exit $code"; exit $code' EXIT

# Print STATUS BLOCK from environment variables or arguments
status_block() {
    cat <<'EOS'
── STATUS BLOCK ──
Time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Mode: ${MODE:-N/A}
Pin: ${ISSUE_ID:-N/A}
Completed: ${DONE:-N/A}
Discovered: ${DISC:-N/A}
Infra: ${INFRA:-N/A}
Next: ${NEXT:-N/A}
──────────────────
EOS
}

# Get PR number from branch name (returns 0 if not found)
gh_pr_head_number() {
    local branch="${1:-}"
    if [[ -z "$branch" ]]; then
        echo 0
        return
    fi
    
    gh pr list --head "$branch" --json number --limit 1 -q '.[0].number // 0' 2>/dev/null || echo 0
}

# Safe echo replacement (uses printf to avoid shell expansion)
safe_echo() {
    printf '%s\n' "$*"
}

# Safe command execution with logging
safe_exec() {
    local cmd="$*"
    safe_echo "[cursor_safe_run] executing: $cmd"
    eval "$cmd"
}

# Validate environment variables for status block
validate_status_env() {
    local required_vars=("MODE" "ISSUE_ID")
    local missing=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        safe_echo "[cursor_safe_run] Warning: Missing environment variables: ${missing[*]}"
        return 1
    fi
    
    return 0
}

# Main function if script is executed directly
main() {
    safe_echo "[cursor_safe_run] Starting quote-safe execution"
    
    # If arguments provided, execute them safely
    if [[ $# -gt 0 ]]; then
        safe_exec "$@"
    else
        safe_echo "[cursor_safe_run] No commands provided"
        status_block
    fi
    
    safe_echo "[cursor_safe_run] Execution complete"
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi