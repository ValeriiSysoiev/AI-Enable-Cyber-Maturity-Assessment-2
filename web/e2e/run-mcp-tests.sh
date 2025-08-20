#!/bin/bash

# MCP Evidence Tests Runner
# Runs MCP-specific evidence tests for Sprint v1.3 validation

set -e

echo "🔧 Running MCP Evidence Preview Tests..."
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "playwright.config.ts" ]; then
    echo -e "${RED}❌ Error: Please run this script from the web/e2e directory${NC}"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
fi

# Run MCP-specific tests
echo -e "${BLUE}🧪 Running MCP Evidence Preview Tests...${NC}"
npx playwright test mcp-evidence-preview.spec.ts --reporter=list

echo ""
echo -e "${BLUE}🔄 Running Backward Compatibility Tests...${NC}"
npx playwright test evidence-backward-compatibility.spec.ts --reporter=list

# Check if both test suites passed
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All MCP evidence tests passed!${NC}"
    echo ""
    echo "Test Summary:"
    echo "- MCP dev badge functionality: ✅"
    echo "- PDF parsing with MCP integration: ✅"
    echo "- Document snippet rendering: ✅"
    echo "- Backward compatibility: ✅"
    echo "- Error handling: ✅"
    echo ""
    echo -e "${BLUE}🚀 Ready for UAT with ?mcp=1 parameter${NC}"
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Please check the output above.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}💡 Usage Tips:${NC}"
echo "- Add ?mcp=1 to any evidence page URL to enable MCP dev mode"
echo "- Look for the purple 'MCP ON' badge in the system status bar"
echo "- Evidence functionality should work identically with/without MCP"
echo ""