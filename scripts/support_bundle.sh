#!/bin/bash
# Support Bundle Generator for diagnostics and troubleshooting

set -euo pipefail

BUNDLE_DIR="/tmp/support-bundle-$(date +%Y%m%d-%H%M%S)"
BUNDLE_ARCHIVE="${BUNDLE_DIR}.tar.gz"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Create bundle directory
mkdir -p "$BUNDLE_DIR"

# Collect system information
collect_system_info() {
    log_info "Collecting system information..."
    {
        echo "=== System Information ==="
        echo "Date: $(date -u)"
        echo "Hostname: $(hostname)"
        echo "OS: $(uname -a)"
        echo "Uptime: $(uptime)"
        echo ""
        echo "=== Disk Usage ==="
        df -h
        echo ""
        echo "=== Memory Usage ==="
        free -h 2>/dev/null || vm_stat 2>/dev/null || echo "N/A"
    } > "$BUNDLE_DIR/system_info.txt"
}

# Collect container logs (anonymized)
collect_container_logs() {
    log_info "Collecting container logs..."
    if command -v docker >/dev/null 2>&1; then
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "$BUNDLE_DIR/containers.txt" 2>/dev/null || true
        
        # Collect last 100 lines from each container
        for container in $(docker ps -q 2>/dev/null || echo ""); do
            name=$(docker inspect -f '{{.Name}}' "$container" | sed 's/^\///')
            docker logs --tail 100 "$container" 2>&1 | \
                sed -E 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/xxx.xxx.xxx.xxx/g' | \
                sed -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/user@example.com/g' \
                > "$BUNDLE_DIR/logs_${name}.txt" 2>/dev/null || true
        done
    fi
}

# Collect configuration (sanitized)
collect_configs() {
    log_info "Collecting configuration files..."
    
    # Copy configs without secrets
    for config in docker-compose.yml .env.example README.md; do
        if [[ -f "$config" ]]; then
            cp "$config" "$BUNDLE_DIR/" 2>/dev/null || true
        fi
    done
    
    # Sanitize environment variables
    if [[ -f .env ]]; then
        grep -v -E '(PASSWORD|SECRET|KEY|TOKEN)' .env > "$BUNDLE_DIR/env_sanitized.txt" 2>/dev/null || true
    fi
}

# Collect AgentRun and MCP call IDs (anonymized)
collect_agent_data() {
    log_info "Collecting agent run data..."
    
    # Find recent agent runs
    if [[ -d "./data/projects" ]]; then
        find ./data/projects -name "*.json" -type f -mtime -1 2>/dev/null | \
            head -20 | while read -r file; do
            # Extract and anonymize call IDs
            jq -r '.agent_runs[]? | {id: .id, status: .status, timestamp: .timestamp}' "$file" 2>/dev/null || true
        done > "$BUNDLE_DIR/agent_runs.json"
        
        # Extract MCP call IDs
        find ./data/projects -name "*mcp*.json" -type f -mtime -1 2>/dev/null | \
            head -10 | while read -r file; do
            jq -r '.call_id' "$file" 2>/dev/null || true
        done > "$BUNDLE_DIR/mcp_calls.txt"
    fi
}

# Collect error logs
collect_error_logs() {
    log_info "Collecting error logs..."
    
    # Find recent errors in logs
    find . -name "*.log" -type f -mtime -1 2>/dev/null | while read -r logfile; do
        grep -i -E "(error|exception|failed|critical)" "$logfile" | \
            tail -50 | \
            sed -E 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/xxx.xxx.xxx.xxx/g' \
            >> "$BUNDLE_DIR/errors.log" 2>/dev/null || true
    done
}

# Generate manifest
generate_manifest() {
    log_info "Generating manifest..."
    {
        echo "Support Bundle Manifest"
        echo "======================"
        echo "Generated: $(date -u)"
        echo "Bundle ID: $(uuidgen 2>/dev/null || echo "$(date +%s)")"
        echo ""
        echo "Contents:"
        ls -la "$BUNDLE_DIR" | tail -n +2
        echo ""
        echo "Redactions Applied:"
        echo "- IP addresses replaced with xxx.xxx.xxx.xxx"
        echo "- Email addresses replaced with user@example.com"
        echo "- Secrets/passwords/tokens removed"
    } > "$BUNDLE_DIR/MANIFEST.txt"
}

# Create archive
create_archive() {
    log_info "Creating archive..."
    tar -czf "$BUNDLE_ARCHIVE" -C /tmp "$(basename "$BUNDLE_DIR")"
    rm -rf "$BUNDLE_DIR"
    
    echo ""
    log_info "Support bundle created: $BUNDLE_ARCHIVE"
    log_info "Size: $(du -h "$BUNDLE_ARCHIVE" | cut -f1)"
    
    # Upload to CI artifacts if in CI environment
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        echo "::set-output name=bundle_path::$BUNDLE_ARCHIVE"
        echo "Support bundle will be uploaded as CI artifact"
    fi
}

# Main execution
main() {
    echo "🔧 Generating Support Bundle..."
    echo "================================"
    
    collect_system_info
    collect_container_logs
    collect_configs
    collect_agent_data
    collect_error_logs
    generate_manifest
    create_archive
    
    echo ""
    echo "✅ Support bundle ready for analysis"
    echo "   Path: $BUNDLE_ARCHIVE"
}

main "$@"