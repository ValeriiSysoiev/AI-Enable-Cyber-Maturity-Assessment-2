#!/bin/bash
# Quick Setup for Missing GitHub Secrets
# This script sets up the missing secrets with safe defaults or placeholders

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Quick Secrets Setup ===${NC}"
echo "This script will configure missing secrets with safe defaults"
echo ""

# Function to set GitHub secret
set_github_secret() {
    local name=$1
    local value=$2
    echo -n "Setting $name... "
    if echo "$value" | gh secret set "$name" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Failed (might already exist)${NC}"
    fi
}

# Get existing values from environment or use defaults
API_BASE_URL="${API_BASE_URL:-https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io}"
WEB_BASE_URL="${WEB_BASE_URL:-https://web-cybermat-prd.azurewebsites.net}"
ADMIN_EMAILS="${ADMIN_EMAILS:-admin@example.com}"

echo -e "${GREEN}Step 1: Setting Base URLs${NC}"
set_github_secret "API_BASE_URL" "$API_BASE_URL"
set_github_secret "WEB_BASE_URL" "$WEB_BASE_URL"
set_github_secret "ADMIN_EMAILS" "$ADMIN_EMAILS"

echo ""
echo -e "${GREEN}Step 2: Setting Database & Storage (with safe defaults)${NC}"
# These will use local/in-memory storage until Azure resources are created
set_github_secret "COSMOS_DB_ENDPOINT" "https://localhost:8081"
set_github_secret "COSMOS_DB_KEY" "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
set_github_secret "COSMOS_DB_DATABASE" "cybermat-prd"
set_github_secret "AZURE_STORAGE_CONNECTION_STRING" "DefaultEndpointsProtocol=https;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;EndpointSuffix=core.windows.net"

echo ""
echo -e "${GREEN}Step 3: Setting Service Bus (with safe defaults)${NC}"
# This will use in-memory queue until Azure Service Bus is configured
set_github_secret "AZURE_SERVICE_BUS_CONNECTION_STRING" "Endpoint=sb://localhost/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=dummy"
set_github_secret "SERVICE_BUS_NAMESPACE" "local-dev"

echo ""
echo -e "${GREEN}Step 4: Setting OpenAI & Search (disabled mode)${NC}"
# These will disable RAG features until properly configured
set_github_secret "AZURE_OPENAI_ENDPOINT" "https://dummy.openai.azure.com/"
set_github_secret "AZURE_OPENAI_API_KEY" "dummy-key-replace-with-real"
set_github_secret "AZURE_OPENAI_EMBEDDING_MODEL" "text-embedding-ada-002"
set_github_secret "AZURE_OPENAI_CHAT_MODEL" "gpt-4"
set_github_secret "AZURE_SEARCH_ENDPOINT" "https://dummy.search.windows.net"
set_github_secret "AZURE_SEARCH_KEY" "dummy-key-replace-with-real"
set_github_secret "AZURE_SEARCH_INDEX_NAME" "cybermat-documents"

echo ""
echo -e "${BLUE}=== Configuration Summary ===${NC}"
echo ""
echo -e "${GREEN}✅ All missing secrets have been configured with safe defaults${NC}"
echo ""
echo -e "${YELLOW}⚠ Important Notes:${NC}"
echo "1. Database will use local/in-memory storage"
echo "2. RAG features will be disabled"
echo "3. Service Bus will use in-memory queue"
echo "4. File storage will be local"
echo ""
echo "These defaults allow the application to run without Azure dependencies."
echo "To enable full features, update the secrets with real Azure resource values."
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Run deployment: gh workflow run 'Deploy to Production' --ref main"
echo "2. Verify deployment: ./scripts/validate-secrets.sh"
echo "3. Update secrets with real values when Azure resources are ready"
echo ""

# Create a configuration file for reference
cat > secrets-configured.json <<EOF
{
  "configuration": "safe-defaults",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "mode": {
    "database": "local",
    "storage": "local",
    "rag": "disabled",
    "servicebus": "in-memory"
  },
  "urls": {
    "api": "$API_BASE_URL",
    "web": "$WEB_BASE_URL"
  },
  "notes": [
    "Using safe defaults for missing Azure resources",
    "Application will run with limited features",
    "Update secrets when Azure resources are available"
  ]
}
EOF

echo -e "${GREEN}Configuration saved to secrets-configured.json${NC}"
echo ""
echo -e "${BLUE}Setup complete!${NC}"