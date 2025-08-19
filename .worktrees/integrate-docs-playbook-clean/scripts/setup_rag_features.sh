#!/bin/bash

# RAG Feature Setup Script
# Configures RAG features based on environment and deployment requirements

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-"development"}
RAG_BACKEND=${2:-"cosmos_db"}
FORCE=${3:-"false"}

echo -e "${BLUE}🚀 Setting up RAG features for environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}📊 Using backend: ${RAG_BACKEND}${NC}"

# Function to set environment variable
set_env_var() {
    local var_name="$1"
    local var_value="$2"
    local description="$3"
    
    echo -e "${GREEN}✓${NC} Setting ${var_name}=${var_value} (${description})"
    export "${var_name}=${var_value}"
}

# Function to validate Azure services
validate_azure_services() {
    echo -e "\n${YELLOW}🔍 Validating Azure service connectivity...${NC}"
    
    # Check if Azure CLI is available
    if ! command -v az &> /dev/null; then
        echo -e "${RED}❌ Azure CLI not found. Please install Azure CLI.${NC}"
        return 1
    fi
    
    # Check Azure login status
    if ! az account show &> /dev/null; then
        echo -e "${YELLOW}⚠️  Not logged into Azure. Please run 'az login'${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} Azure CLI authenticated"
    
    # Validate Azure OpenAI if configured
    if [[ -n "${AZURE_OPENAI_ENDPOINT:-}" ]]; then
        echo -e "${BLUE}📝 Validating Azure OpenAI endpoint...${NC}"
        if curl -sf "${AZURE_OPENAI_ENDPOINT}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Azure OpenAI endpoint accessible"
        else
            echo -e "${YELLOW}⚠️  Azure OpenAI endpoint may not be accessible${NC}"
        fi
    fi
    
    # Validate Azure Search if configured
    if [[ -n "${AZURE_SEARCH_ENDPOINT:-}" ]]; then
        echo -e "${BLUE}🔍 Validating Azure Search endpoint...${NC}"
        if curl -sf "${AZURE_SEARCH_ENDPOINT}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Azure Search endpoint accessible"
        else
            echo -e "${YELLOW}⚠️  Azure Search endpoint may not be accessible${NC}"
        fi
    fi
    
    # Validate Cosmos DB if configured
    if [[ -n "${COSMOS_ENDPOINT:-}" ]]; then
        echo -e "${BLUE}🗄️  Validating Cosmos DB endpoint...${NC}"
        if curl -sf "${COSMOS_ENDPOINT}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Cosmos DB endpoint accessible"
        else
            echo -e "${YELLOW}⚠️  Cosmos DB endpoint may not be accessible${NC}"
        fi
    fi
}

# Function to configure production settings
configure_production() {
    echo -e "\n${BLUE}🏭 Configuring production RAG settings...${NC}"
    
    set_env_var "RAG_MODE" "azure_openai" "Enable RAG with Azure OpenAI"
    set_env_var "RAG_FEATURE_FLAG" "true" "Enable RAG feature flag"
    set_env_var "RAG_SEARCH_BACKEND" "azure_search" "Use Azure Search for production"
    set_env_var "RAG_SEARCH_TOP_K" "10" "Production search result limit"
    set_env_var "RAG_SIMILARITY_THRESHOLD" "0.7" "High-quality results only"
    set_env_var "RAG_USE_HYBRID_SEARCH" "true" "Enable hybrid search"
    set_env_var "RAG_RERANK_ENABLED" "true" "Enable semantic reranking"
    set_env_var "RAG_CHUNK_SIZE" "1500" "Optimal chunk size for production"
    set_env_var "RAG_CHUNK_OVERLAP" "0.1" "10% chunk overlap"
    set_env_var "RAG_RATE_LIMIT" "100" "Production rate limit"
    set_env_var "RAG_MAX_DOCUMENT_LENGTH" "100000" "Max document size"
    
    # Validate required Azure services
    validate_azure_services
}

# Function to configure staging settings
configure_staging() {
    echo -e "\n${BLUE}🧪 Configuring staging RAG settings...${NC}"
    
    set_env_var "RAG_MODE" "azure_openai" "Enable RAG with Azure OpenAI"
    set_env_var "RAG_FEATURE_FLAG" "true" "Enable RAG feature flag"
    set_env_var "RAG_SEARCH_BACKEND" "${RAG_BACKEND}" "Use specified backend"
    set_env_var "RAG_SEARCH_TOP_K" "8" "Staging search result limit"
    set_env_var "RAG_SIMILARITY_THRESHOLD" "0.6" "Lower threshold for testing"
    set_env_var "RAG_USE_HYBRID_SEARCH" "true" "Enable hybrid search"
    set_env_var "RAG_RERANK_ENABLED" "false" "Disable reranking for cost"
    set_env_var "RAG_CHUNK_SIZE" "1200" "Smaller chunks for testing"
    set_env_var "RAG_CHUNK_OVERLAP" "0.15" "15% chunk overlap"
    set_env_var "RAG_RATE_LIMIT" "50" "Lower rate limit for staging"
    set_env_var "RAG_MAX_DOCUMENT_LENGTH" "50000" "Smaller max document size"
    
    validate_azure_services
}

# Function to configure development settings
configure_development() {
    echo -e "\n${BLUE}💻 Configuring development RAG settings...${NC}"
    
    set_env_var "RAG_MODE" "azure_openai" "Enable RAG with Azure OpenAI"
    set_env_var "RAG_FEATURE_FLAG" "true" "Enable RAG feature flag"
    set_env_var "RAG_SEARCH_BACKEND" "cosmos_db" "Use Cosmos DB for development"
    set_env_var "RAG_SEARCH_TOP_K" "5" "Development search result limit"
    set_env_var "RAG_SIMILARITY_THRESHOLD" "0.5" "Lower threshold for development"
    set_env_var "RAG_USE_HYBRID_SEARCH" "false" "Disable hybrid search"
    set_env_var "RAG_RERANK_ENABLED" "false" "Disable reranking"
    set_env_var "RAG_CHUNK_SIZE" "800" "Smaller chunks for development"
    set_env_var "RAG_CHUNK_OVERLAP" "0.2" "20% chunk overlap"
    set_env_var "RAG_RATE_LIMIT" "25" "Low rate limit for development"
    set_env_var "RAG_MAX_DOCUMENT_LENGTH" "25000" "Small max document size"
    set_env_var "RAG_COSMOS_CONTAINER" "embeddings-dev" "Development container"
    
    echo -e "${GREEN}✓${NC} Development mode uses Cosmos DB - no Azure Search validation needed"
}

# Function to configure demo settings
configure_demo() {
    echo -e "\n${BLUE}🎭 Configuring demo RAG settings...${NC}"
    
    set_env_var "RAG_MODE" "none" "Disable RAG for simplified demo"
    set_env_var "RAG_FEATURE_FLAG" "false" "Disable RAG feature flag"
    
    echo -e "${GREEN}✓${NC} Demo mode disables RAG for simplified experience"
}

# Function to disable RAG
configure_disabled() {
    echo -e "\n${BLUE}🚫 Disabling RAG features...${NC}"
    
    set_env_var "RAG_MODE" "none" "Disable RAG functionality"
    set_env_var "RAG_FEATURE_FLAG" "false" "Disable RAG feature flag"
    
    echo -e "${GREEN}✓${NC} RAG functionality disabled"
}

# Function to create Azure Search index
create_azure_search_index() {
    if [[ "${RAG_BACKEND}" == "azure_search" && -n "${AZURE_SEARCH_ENDPOINT:-}" ]]; then
        echo -e "\n${YELLOW}🏗️  Creating Azure Search index...${NC}"
        
        # Check if index already exists
        local index_name="${AZURE_SEARCH_INDEX_NAME:-eng-docs}"
        local search_endpoint="${AZURE_SEARCH_ENDPOINT}"
        
        echo -e "${BLUE}📝 Index name: ${index_name}${NC}"
        echo -e "${BLUE}📍 Endpoint: ${search_endpoint}${NC}"
        
        # Create index via API call (requires the application to be running)
        echo -e "${YELLOW}ℹ️  To create the index, run this after starting the application:${NC}"
        echo -e "${BLUE}curl -X POST -H 'X-User-Email: admin@example.com' -H 'X-Engagement-ID: setup' '${search_endpoint}/api/admin/rag/index/create'${NC}"
    fi
}

# Function to generate environment file
generate_env_file() {
    local env_file=".env.rag.${ENVIRONMENT}"
    echo -e "\n${YELLOW}📄 Generating environment file: ${env_file}${NC}"
    
    cat > "${env_file}" << EOF
# RAG Configuration for ${ENVIRONMENT}
# Generated by setup_rag_features.sh on $(date)

# Core RAG Settings
RAG_MODE=${RAG_MODE:-none}
RAG_FEATURE_FLAG=${RAG_FEATURE_FLAG:-false}
RAG_SEARCH_BACKEND=${RAG_SEARCH_BACKEND:-cosmos_db}

# Search Parameters
RAG_SEARCH_TOP_K=${RAG_SEARCH_TOP_K:-5}
RAG_SIMILARITY_THRESHOLD=${RAG_SIMILARITY_THRESHOLD:-0.5}
RAG_USE_HYBRID_SEARCH=${RAG_USE_HYBRID_SEARCH:-false}
RAG_RERANK_ENABLED=${RAG_RERANK_ENABLED:-false}

# Embedding Settings
RAG_CHUNK_SIZE=${RAG_CHUNK_SIZE:-800}
RAG_CHUNK_OVERLAP=${RAG_CHUNK_OVERLAP:-0.2}
RAG_RATE_LIMIT=${RAG_RATE_LIMIT:-25}
RAG_MAX_DOCUMENT_LENGTH=${RAG_MAX_DOCUMENT_LENGTH:-25000}

# Azure OpenAI (configure these manually)
# AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
# AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
# AZURE_OPENAI_EMBEDDING_DIMENSIONS=3072

# Azure Search (configure these manually)
# AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
# AZURE_SEARCH_API_KEY=your-api-key
# AZURE_SEARCH_INDEX_NAME=eng-docs

# Cosmos DB (configure these manually)
# COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
# COSMOS_DATABASE=cybermaturity
RAG_COSMOS_CONTAINER=${RAG_COSMOS_CONTAINER:-embeddings}
EOF

    echo -e "${GREEN}✓${NC} Environment file created: ${env_file}"
    echo -e "${YELLOW}ℹ️  Please update Azure service endpoints and keys manually${NC}"
}

# Function to test RAG configuration
test_rag_configuration() {
    echo -e "\n${YELLOW}🧪 Testing RAG configuration...${NC}"
    
    # Basic configuration check
    if [[ "${RAG_MODE}" == "azure_openai" ]]; then
        if [[ -z "${AZURE_OPENAI_ENDPOINT:-}" ]]; then
            echo -e "${YELLOW}⚠️  AZURE_OPENAI_ENDPOINT not configured${NC}"
        else
            echo -e "${GREEN}✓${NC} Azure OpenAI endpoint configured"
        fi
        
        if [[ "${RAG_SEARCH_BACKEND}" == "azure_search" && -z "${AZURE_SEARCH_ENDPOINT:-}" ]]; then
            echo -e "${YELLOW}⚠️  AZURE_SEARCH_ENDPOINT not configured${NC}"
        elif [[ "${RAG_SEARCH_BACKEND}" == "azure_search" ]]; then
            echo -e "${GREEN}✓${NC} Azure Search endpoint configured"
        fi
        
        if [[ "${RAG_SEARCH_BACKEND}" == "cosmos_db" && -z "${COSMOS_ENDPOINT:-}" ]]; then
            echo -e "${YELLOW}⚠️  COSMOS_ENDPOINT not configured${NC}"
        elif [[ "${RAG_SEARCH_BACKEND}" == "cosmos_db" ]]; then
            echo -e "${GREEN}✓${NC} Cosmos DB endpoint configured"
        fi
    else
        echo -e "${GREEN}✓${NC} RAG disabled - no endpoint validation needed"
    fi
}

# Function to show configuration summary
show_summary() {
    echo -e "\n${BLUE}📋 RAG Configuration Summary${NC}"
    echo -e "${BLUE}=============================${NC}"
    echo -e "Environment: ${ENVIRONMENT}"
    echo -e "RAG Mode: ${RAG_MODE:-none}"
    echo -e "Feature Flag: ${RAG_FEATURE_FLAG:-false}"
    echo -e "Search Backend: ${RAG_SEARCH_BACKEND:-none}"
    echo -e "Top K Results: ${RAG_SEARCH_TOP_K:-0}"
    echo -e "Similarity Threshold: ${RAG_SIMILARITY_THRESHOLD:-0.0}"
    echo -e "Hybrid Search: ${RAG_USE_HYBRID_SEARCH:-false}"
    echo -e "Reranking: ${RAG_RERANK_ENABLED:-false}"
    echo -e "Chunk Size: ${RAG_CHUNK_SIZE:-0}"
    echo -e "Rate Limit: ${RAG_RATE_LIMIT:-0}"
    
    echo -e "\n${YELLOW}📝 Next Steps:${NC}"
    if [[ "${RAG_MODE}" == "azure_openai" ]]; then
        echo -e "1. Configure Azure service endpoints and keys"
        echo -e "2. Load environment variables: source .env.rag.${ENVIRONMENT}"
        echo -e "3. Start the application"
        if [[ "${RAG_SEARCH_BACKEND}" == "azure_search" ]]; then
            echo -e "4. Create Azure Search index via API"
        fi
        echo -e "5. Test RAG functionality via UI or API"
    else
        echo -e "1. RAG is disabled - application will run without RAG features"
        echo -e "2. To enable RAG, reconfigure with appropriate environment"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🔧 AI-Enabled Cyber Maturity Assessment - RAG Setup${NC}"
    echo -e "${BLUE}=====================================================${NC}"
    
    case "${ENVIRONMENT}" in
        "production"|"prod")
            configure_production
            ;;
        "staging"|"stage")
            configure_staging
            ;;
        "development"|"dev")
            configure_development
            ;;
        "demo")
            configure_demo
            ;;
        "disabled"|"none")
            configure_disabled
            ;;
        *)
            echo -e "${RED}❌ Unknown environment: ${ENVIRONMENT}${NC}"
            echo -e "${YELLOW}Valid environments: production, staging, development, demo, disabled${NC}"
            exit 1
            ;;
    esac
    
    generate_env_file
    create_azure_search_index
    test_rag_configuration
    show_summary
    
    echo -e "\n${GREEN}🎉 RAG feature setup complete!${NC}"
}

# Show usage if requested
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "RAG Feature Setup Script"
    echo ""
    echo "Usage: $0 [environment] [backend] [force]"
    echo ""
    echo "Environments:"
    echo "  production    - Production settings with Azure Search"
    echo "  staging       - Staging settings with configurable backend"
    echo "  development   - Development settings with Cosmos DB"
    echo "  demo          - Demo settings (RAG disabled)"
    echo "  disabled      - Disable RAG entirely"
    echo ""
    echo "Backends:"
    echo "  azure_search  - Use Azure Cognitive Search (recommended for production)"
    echo "  cosmos_db     - Use Cosmos DB with vector search (for development)"
    echo ""
    echo "Examples:"
    echo "  $0 production azure_search"
    echo "  $0 development cosmos_db"
    echo "  $0 demo"
    echo "  $0 disabled"
    exit 0
fi

# Execute main function
main "$@"