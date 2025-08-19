#!/usr/bin/env bash
#
# Idempotent Cosmos DB setup for S4 features
# Creates containers if they don't exist, skips if they do
#

set -euo pipefail

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "S4 Cosmos DB Container Setup"
echo "========================================"

# Check required environment variables
required_vars=(
    "COSMOS_ENDPOINT"
    "COSMOS_DATABASE"
    "AZURE_SUBSCRIPTION_ID"
    "AZURE_RESOURCE_GROUP"
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo -e "${RED}Error: $var is not set${NC}"
        exit 1
    fi
done

COSMOS_ACCOUNT=$(echo "$COSMOS_ENDPOINT" | sed 's|https://||' | sed 's|\.documents\.azure\.com.*||')
DATABASE="${COSMOS_DATABASE:-cybermaturity}"

echo "Cosmos Account: $COSMOS_ACCOUNT"
echo "Database: $DATABASE"
echo "Resource Group: $AZURE_RESOURCE_GROUP"
echo ""

# Function to create container if it doesn't exist
create_container_if_not_exists() {
    local container_name=$1
    local partition_key=$2
    local ttl=${3:-}
    
    echo -n "Checking container '$container_name'... "
    
    # Check if container exists
    if az cosmosdb sql container show \
        --account-name "$COSMOS_ACCOUNT" \
        --database-name "$DATABASE" \
        --name "$container_name" \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --output none 2>/dev/null; then
        echo -e "${GREEN}exists${NC}"
    else
        echo -e "${YELLOW}creating${NC}"
        
        # Build create command
        create_cmd="az cosmosdb sql container create \
            --account-name '$COSMOS_ACCOUNT' \
            --database-name '$DATABASE' \
            --name '$container_name' \
            --partition-key-path '$partition_key' \
            --resource-group '$AZURE_RESOURCE_GROUP' \
            --throughput 400"
        
        # Add TTL if specified
        if [[ -n "$ttl" ]]; then
            create_cmd="$create_cmd --ttl $ttl"
        fi
        
        # Execute create command
        eval "$create_cmd" > /dev/null
        echo -e "  ${GREEN}✓ Created container '$container_name'${NC}"
    fi
}

echo "Setting up S4 containers..."
echo ""

# S4 Feature Containers
# Format: container_name partition_key [ttl_seconds]

# Service Bus queuing (from s4-servicebus-scaffold-adr)
# Note: Service Bus itself uses native Azure Service Bus, not Cosmos
# These containers support async orchestration state tracking

# CSF Framework (from s4-csf-grid-skeleton)
# No new containers needed - CSF data is static JSON

# Workshops (from s4-workshops-consent)
create_container_if_not_exists "workshops" "/engagement_id"

# Minutes (from s4-minutes-publish-immutable)
create_container_if_not_exists "minutes" "/workshop_id"

# Chat & Run Cards (from s4-chat-shell-commands)
create_container_if_not_exists "chat_messages" "/engagement_id" "7776000"  # 90 days TTL
create_container_if_not_exists "run_cards" "/engagement_id" "15552000"    # 180 days TTL

# Evidence (already exists but verify)
create_container_if_not_exists "evidence" "/engagement_id"

echo ""
echo -e "${GREEN}✓ S4 Cosmos containers setup complete${NC}"
echo ""

# Verify all containers
echo "Verifying all containers..."
containers=(
    "engagements"
    "memberships"
    "assessments"
    "questions"
    "responses"
    "findings"
    "recommendations"
    "documents"
    "runlogs"
    "background_jobs"
    "audit_logs"
    "embeddings"
    "workshops"
    "minutes"
    "chat_messages"
    "run_cards"
    "evidence"
)

all_exist=true
for container in "${containers[@]}"; do
    if az cosmosdb sql container show \
        --account-name "$COSMOS_ACCOUNT" \
        --database-name "$DATABASE" \
        --name "$container" \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --output none 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $container"
    else
        echo -e "  ${RED}✗${NC} $container"
        all_exist=false
    fi
done

echo ""
if $all_exist; then
    echo -e "${GREEN}✓ All containers verified successfully${NC}"
    exit 0
else
    echo -e "${RED}✗ Some containers are missing${NC}"
    exit 1
fi