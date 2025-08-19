#!/usr/bin/env bash
#
# Seed CSF 2.0 taxonomy data
# Idempotent - can be run multiple times safely
#

set -euo pipefail

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "CSF 2.0 Taxonomy Seeding"
echo "========================================"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CSF_DATA_FILE="$PROJECT_ROOT/app/data/csf2.json"

# Check if CSF data file exists
if [[ ! -f "$CSF_DATA_FILE" ]]; then
    echo -e "${YELLOW}Warning: CSF data file not found at $CSF_DATA_FILE${NC}"
    echo "The CSF taxonomy is loaded from static JSON at runtime."
    echo "No database seeding required for CSF data."
    exit 0
fi

echo "CSF 2.0 data file found: $CSF_DATA_FILE"
echo ""

# Validate JSON structure
echo -n "Validating CSF JSON structure... "
if python3 -c "import json; json.load(open('$CSF_DATA_FILE'))" 2>/dev/null; then
    echo -e "${GREEN}valid${NC}"
else
    echo -e "${RED}invalid${NC}"
    echo "Error: CSF data file contains invalid JSON"
    exit 1
fi

# Extract statistics
echo ""
echo "CSF 2.0 Taxonomy Statistics:"
python3 << EOF
import json

with open('$CSF_DATA_FILE', 'r') as f:
    data = json.load(f)
    
print(f"  Functions: {len(data['functions'])}")

total_categories = 0
total_subcategories = 0

for function in data['functions']:
    categories = function.get('categories', [])
    total_categories += len(categories)
    
    for category in categories:
        subcategories = category.get('subcategories', [])
        total_subcategories += len(subcategories)

print(f"  Categories: {total_categories}")
print(f"  Subcategories: {total_subcategories}")
EOF

echo ""
echo -e "${GREEN}✓ CSF 2.0 taxonomy is ready${NC}"
echo ""
echo "Note: CSF data is served from static JSON via the /api/csf endpoints."
echo "No database seeding is required. The data is loaded at application startup."
echo ""

# Optional: Warm up the CSF service if API is running
if [[ -n "${API_BASE_URL:-}" ]]; then
    echo "Testing CSF API endpoint..."
    if curl -s "$API_BASE_URL/api/csf/functions" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ CSF API is responding${NC}"
    else
        echo -e "${YELLOW}⚠ CSF API is not available (this is OK if the API is not running)${NC}"
    fi
fi

exit 0