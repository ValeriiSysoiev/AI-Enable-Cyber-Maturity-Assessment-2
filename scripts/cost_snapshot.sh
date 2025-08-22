#!/bin/bash
# Azure Cost Snapshot Script
# Retrieves current spending and budget status

set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-artifacts/cost}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-}"
DRY_RUN="${DRY_RUN:-false}"

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

if [[ "$DRY_RUN" == "true" || -z "$SUBSCRIPTION_ID" ]]; then
    echo "📊 [DRY RUN] Cost snapshot would retrieve:"
    echo "  - Current month spending"
    echo "  - Budget utilization"
    echo "  - Resource group costs"
    echo "  - Trending analysis"
    
    cat > "$OUTPUT_DIR/cost-snapshot-$TIMESTAMP.json" << 'EOF'
{
  "timestamp": "DRY_RUN",
  "subscription": "placeholder",
  "current_spending": 150.25,
  "budget_limit": 500.00,
  "utilization_percent": 30.05,
  "status": "within_budget"
}
EOF
    echo "📄 Sample report saved to $OUTPUT_DIR/"
    exit 0
fi

echo "💰 Retrieving Azure cost data..."

# Get current month costs
az consumption usage list \
    --subscription "$SUBSCRIPTION_ID" \
    --top 100 \
    > "$OUTPUT_DIR/usage-$TIMESTAMP.json"

# Get budget status if available
az consumption budget list \
    --subscription "$SUBSCRIPTION_ID" \
    > "$OUTPUT_DIR/budgets-$TIMESTAMP.json" 2>/dev/null || echo '[]' > "$OUTPUT_DIR/budgets-$TIMESTAMP.json"

echo "✅ Cost snapshot saved to $OUTPUT_DIR/"