#!/bin/bash
# Generate Release Notes from Git History and Conventional Commits

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PREVIOUS_TAG="${1:-}"
OUTPUT_FILE="${2:-RELEASE_NOTES.md}"
REPO_URL="https://github.com/ValeriiSysoiev/AI-Enable-Cyber-Maturity-Assessment-2"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_header() { echo -e "${BLUE}$1${NC}"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Get the previous tag if not provided
get_previous_tag() {
    if [[ -z "$PREVIOUS_TAG" ]]; then
        PREVIOUS_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "")
        if [[ -z "$PREVIOUS_TAG" ]]; then
            # No previous tags, use first commit
            PREVIOUS_TAG=$(git rev-list --max-parents=0 HEAD)
            log_warn "No previous tags found, using first commit"
        else
            log_info "Using previous tag: $PREVIOUS_TAG"
        fi
    fi
}

# Parse conventional commits
parse_commits() {
    local range="${PREVIOUS_TAG}..HEAD"
    
    # Categories for conventional commits
    declare -A categories
    categories[feat]="🚀 New Features"
    categories[fix]="🐛 Bug Fixes"
    categories[docs]="📚 Documentation"
    categories[style]="💄 Style Changes"
    categories[refactor]="♻️ Code Refactoring"
    categories[perf]="⚡ Performance Improvements"
    categories[test]="🧪 Tests"
    categories[chore]="🔧 Chores"
    categories[ci]="👷 CI/CD"
    categories[security]="🔒 Security"
    
    # Get commits in range
    local commits=$(git log --pretty=format:"%h|%s|%an|%ad" --date=short "$range" 2>/dev/null || echo "")
    
    if [[ -z "$commits" ]]; then
        log_warn "No commits found in range $range"
        return
    fi
    
    # Parse commits by type
    for type in "${!categories[@]}"; do
        local type_commits=$(echo "$commits" | grep "^[a-f0-9]*|$type" || echo "")
        
        if [[ -n "$type_commits" ]]; then
            echo "## ${categories[$type]}"
            echo ""
            
            echo "$type_commits" | while IFS="|" read -r hash subject author date; do
                # Clean up subject (remove type prefix)
                local clean_subject=$(echo "$subject" | sed -E "s/^$type(\([^)]*\))?: *//")
                echo "- $clean_subject ([${hash}]($REPO_URL/commit/${hash})) - $author"
            done
            echo ""
        fi
    done
    
    # Other commits (not following conventional commits)
    local other_commits=$(echo "$commits" | grep -v -E "^[a-f0-9]*\|(feat|fix|docs|style|refactor|perf|test|chore|ci|security)" || echo "")
    
    if [[ -n "$other_commits" ]]; then
        echo "## 📝 Other Changes"
        echo ""
        echo "$other_commits" | while IFS="|" read -r hash subject author date; do
            echo "- $subject ([${hash}]($REPO_URL/commit/${hash})) - $author"
        done
        echo ""
    fi
}

# Generate statistics
generate_stats() {
    local range="${PREVIOUS_TAG}..HEAD"
    
    echo "## 📊 Release Statistics"
    echo ""
    
    # Commit count
    local commit_count=$(git rev-list --count "$range" 2>/dev/null || echo "0")
    echo "- **Commits**: $commit_count"
    
    # Contributors
    local contributors=$(git log --pretty=format:"%an" "$range" 2>/dev/null | sort -u | wc -l || echo "0")
    echo "- **Contributors**: $contributors"
    
    # Files changed
    local files_changed=$(git diff --name-only "$PREVIOUS_TAG" HEAD 2>/dev/null | wc -l || echo "0")
    echo "- **Files Changed**: $files_changed"
    
    # Lines changed
    local stats=$(git diff --shortstat "$PREVIOUS_TAG" HEAD 2>/dev/null || echo "")
    if [[ -n "$stats" ]]; then
        echo "- **Changes**: $stats"
    fi
    
    echo ""
}

# Generate header
generate_header() {
    local current_tag=$(git describe --tags --exact-match HEAD 2>/dev/null || echo "Unreleased")
    local current_date=$(date +%Y-%m-%d)
    
    echo "# Release Notes"
    echo ""
    echo "## $current_tag - $current_date"
    echo ""
    
    if [[ "$current_tag" != "Unreleased" ]]; then
        echo "**Full Changelog**: [$PREVIOUS_TAG...$current_tag]($REPO_URL/compare/$PREVIOUS_TAG...$current_tag)"
    else
        echo "**Development Build** - Changes since $PREVIOUS_TAG"
    fi
    echo ""
}

# Generate breaking changes section
generate_breaking_changes() {
    local range="${PREVIOUS_TAG}..HEAD"
    
    # Look for BREAKING CHANGE in commit messages
    local breaking_commits=$(git log --grep="BREAKING CHANGE" --pretty=format:"%h|%s|%b" "$range" 2>/dev/null || echo "")
    
    if [[ -n "$breaking_commits" ]]; then
        echo "## ⚠️ Breaking Changes"
        echo ""
        
        echo "$breaking_commits" | while IFS="|" read -r hash subject body; do
            echo "- **$subject** ([${hash}]($REPO_URL/commit/${hash}))"
            # Extract breaking change description from body
            local breaking_desc=$(echo "$body" | grep -A5 "BREAKING CHANGE:" | tail -n+2 || echo "")
            if [[ -n "$breaking_desc" ]]; then
                echo "  $breaking_desc"
            fi
            echo ""
        done
    fi
}

# Main generation function
generate_release_notes() {
    log_info "Generating release notes to $OUTPUT_FILE"
    
    {
        generate_header
        generate_breaking_changes
        parse_commits
        generate_stats
        
        echo "---"
        echo ""
        echo "*Generated automatically from git history and conventional commits*"
        echo "*Generated on $(date -u '+%Y-%m-%d %H:%M:%S UTC')*"
        
    } > "$OUTPUT_FILE"
    
    log_info "Release notes generated successfully"
    
    # Show preview
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo ""
        log_header "Preview:"
        echo ""
        head -30 "$OUTPUT_FILE"
        if [[ $(wc -l < "$OUTPUT_FILE") -gt 30 ]]; then
            echo "..."
            echo "(truncated - see $OUTPUT_FILE for full content)"
        fi
    fi
}

# Main execution
main() {
    echo "📝 Release Notes Generator"
    echo "========================="
    echo ""
    
    get_previous_tag
    generate_release_notes
    
    echo ""
    log_info "Release notes ready: $OUTPUT_FILE"
}

main "$@"