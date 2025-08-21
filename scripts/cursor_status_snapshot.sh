#!/bin/bash
# Cursor Status Snapshot - Generate status blocks safely from environment

set -Eeuo pipefail

# Source the safe runner functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cursor_safe_run.sh
source "$SCRIPT_DIR/cursor_safe_run.sh"

# Generate status snapshot from environment variables
generate_status_snapshot() {
    # Capture current environment for status block
    local timestamp
    timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    
    # Use heredoc to avoid quote issues
    cat <<EOF
── CURSOR STATUS SNAPSHOT ──
Generated: $timestamp
Mode: ${MODE:-development}
Issue Pin: ${ISSUE_ID:-none}
Completed Tasks: ${DONE:-0}
Discovered Issues: ${DISC:-0}
Infrastructure Status: ${INFRA:-unknown}
Next Action: ${NEXT:-planning}
Git Branch: $(git branch --show-current 2>/dev/null || echo "detached")
Git Status: $(git status --porcelain | wc -l | tr -d ' ') uncommitted changes
──────────────────────────────
EOF
}

# Main execution
main() {
    echo "[cursor_status_snapshot] Generating status from environment"
    
    # Validate required environment variables
    validate_status_env || echo "[cursor_status_snapshot] Warning: Some environment variables missing"
    
    # Generate and display status
    generate_status_snapshot
    
    echo "[cursor_status_snapshot] Status snapshot complete"
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi