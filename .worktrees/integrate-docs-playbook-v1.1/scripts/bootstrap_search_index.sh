#!/bin/bash

# Azure AI Search Index Bootstrap Script
# Creates the eng-docs search index with vector search capabilities

set -e

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh" 2>/dev/null || echo "Warning: common.sh not found"

# Configuration
INDEX_NAME="eng-docs"
SEARCH_API_VERSION="2023-11-01"

# Check if required environment variables are set
check_env_vars() {
    local required_vars=("AZURE_SEARCH_SERVICE_NAME" "AZURE_SEARCH_ADMIN_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            echo "Error: Environment variable $var is not set"
            echo "Please set the following variables:"
            echo "  export AZURE_SEARCH_SERVICE_NAME=<your-search-service-name>"
            echo "  export AZURE_SEARCH_ADMIN_KEY=<your-search-admin-key>"
            exit 1
        fi
    done
}

# Create the search index
create_search_index() {
    echo "Creating Azure AI Search index: $INDEX_NAME"
    
    local search_endpoint="https://${AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
    local index_url="${search_endpoint}/indexes/${INDEX_NAME}?api-version=${SEARCH_API_VERSION}"
    
    # Index definition with vector search capabilities
    local index_definition='{
        "name": "'${INDEX_NAME}'",
        "fields": [
            {
                "name": "id",
                "type": "Edm.String",
                "key": true,
                "filterable": true,
                "retrievable": true,
                "searchable": false
            },
            {
                "name": "engagement_id",
                "type": "Edm.String",
                "filterable": true,
                "retrievable": true,
                "searchable": false
            },
            {
                "name": "doc_id",
                "type": "Edm.String",
                "filterable": true,
                "retrievable": true,
                "searchable": false
            },
            {
                "name": "chunk_id",
                "type": "Edm.String",
                "filterable": false,
                "retrievable": true,
                "searchable": false
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": true,
                "retrievable": true,
                "analyzer": "en.microsoft"
            },
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": true,
                "retrievable": false,
                "dimensions": 3072,
                "vectorSearchProfile": "vector-profile"
            },
            {
                "name": "source_uri",
                "type": "Edm.String",
                "retrievable": true,
                "searchable": false
            },
            {
                "name": "uploaded_at",
                "type": "Edm.DateTimeOffset",
                "filterable": true,
                "sortable": true,
                "retrievable": true
            },
            {
                "name": "tags",
                "type": "Collection(Edm.String)",
                "filterable": true,
                "retrievable": true,
                "searchable": true
            }
        ],
        "vectorSearch": {
            "profiles": [
                {
                    "name": "vector-profile",
                    "algorithm": "vector-algorithm"
                }
            ],
            "algorithms": [
                {
                    "name": "vector-algorithm",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ]
        },
        "semantic": {
            "configurations": [
                {
                    "name": "semantic-config",
                    "prioritizedFields": {
                        "titleField": {
                            "fieldName": "doc_id"
                        },
                        "contentFields": [
                            {
                                "fieldName": "content"
                            }
                        ],
                        "keywordsFields": [
                            {
                                "fieldName": "tags"
                            }
                        ]
                    }
                }
            ]
        }
    }'
    
    # Create or update the index
    local response
    response=$(curl -s -w "%{http_code}" -X PUT \
        -H "Content-Type: application/json" \
        -H "api-key: $AZURE_SEARCH_ADMIN_KEY" \
        -d "$index_definition" \
        "$index_url")
    
    local http_code="${response: -3}"
    local response_body="${response%???}"
    
    if [[ "$http_code" =~ ^(200|201)$ ]]; then
        echo "✓ Search index '$INDEX_NAME' created successfully"
        echo "Response: $response_body" | jq '.' 2>/dev/null || echo "$response_body"
    else
        echo "✗ Failed to create search index. HTTP Code: $http_code"
        echo "Response: $response_body"
        exit 1
    fi
}

# Verify the index was created
verify_index() {
    echo "Verifying search index..."
    
    local search_endpoint="https://${AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
    local index_url="${search_endpoint}/indexes/${INDEX_NAME}?api-version=${SEARCH_API_VERSION}"
    
    local response
    response=$(curl -s -w "%{http_code}" -X GET \
        -H "api-key: $AZURE_SEARCH_ADMIN_KEY" \
        "$index_url")
    
    local http_code="${response: -3}"
    local response_body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        echo "✓ Search index verified successfully"
        local field_count
        field_count=$(echo "$response_body" | jq '.fields | length' 2>/dev/null || echo "unknown")
        echo "  - Index has $field_count fields"
        echo "  - Vector search enabled: $(echo "$response_body" | jq '.vectorSearch != null' 2>/dev/null || echo "unknown")"
        echo "  - Semantic search enabled: $(echo "$response_body" | jq '.semantic != null' 2>/dev/null || echo "unknown")"
    else
        echo "✗ Failed to verify search index. HTTP Code: $http_code"
        echo "Response: $response_body"
        exit 1
    fi
}

# Main execution
main() {
    echo "=== Azure AI Search Index Bootstrap ==="
    echo "Search Service: $AZURE_SEARCH_SERVICE_NAME"
    echo "Index Name: $INDEX_NAME"
    echo
    
    check_env_vars
    create_search_index
    verify_index
    
    echo
    echo "=== Bootstrap Complete ==="
    echo "The search index is ready for use by the application."
    echo "To populate the index, use the document ingestion API endpoints."
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi