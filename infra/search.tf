# Azure AI Search Service
resource "azurerm_search_service" "search" {
  name                = "search-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  location           = local.location
  sku                = var.search_service_tier
  replica_count      = var.search_replica_count
  partition_count    = var.search_partition_count

  # Enable semantic search capabilities
  semantic_search_sku = var.search_service_tier == "basic" ? null : "standard"
  
  # Network security - allow public access for now, can be restricted later
  public_network_access_enabled = true
  
  # Disable local authentication to enforce RBAC
  local_authentication_enabled = false
  
  tags = local.common_tags
}

# Generate a random suffix for unique naming
resource "random_string" "search_index" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}

# Note: Search index will be created via API calls from the application
# This is because the azapi provider doesn't support the current Search API version
# The index schema is documented here for reference and will be implemented
# in the bootstrap script

# Search Index Schema for reference:
# {
#   "name": "eng-docs",
#   "fields": [
#     {"name": "id", "type": "Edm.String", "key": true, "filterable": true, "retrievable": true},
#     {"name": "engagement_id", "type": "Edm.String", "filterable": true, "retrievable": true, "searchable": false},
#     {"name": "doc_id", "type": "Edm.String", "filterable": true, "retrievable": true, "searchable": false},
#     {"name": "chunk_id", "type": "Edm.String", "filterable": false, "retrievable": true, "searchable": false},
#     {"name": "content", "type": "Edm.String", "searchable": true, "retrievable": true, "analyzer": "en.microsoft"},
#     {"name": "content_vector", "type": "Collection(Edm.Single)", "searchable": true, "retrievable": false, "dimensions": 3072, "vectorSearchProfile": "vector-profile"},
#     {"name": "source_uri", "type": "Edm.String", "retrievable": true, "searchable": false},
#     {"name": "uploaded_at", "type": "Edm.DateTimeOffset", "filterable": true, "sortable": true, "retrievable": true},
#     {"name": "tags", "type": "Collection(Edm.String)", "filterable": true, "retrievable": true, "searchable": true}
#   ],
#   "vectorSearch": {
#     "profiles": [{"name": "vector-profile", "algorithm": "vector-algorithm"}],
#     "algorithms": [{"name": "vector-algorithm", "kind": "hnsw", "hnswParameters": {"metric": "cosine", "m": 4, "efConstruction": 400, "efSearch": 500}}]
#   },
#   "semantic": {"configurations": [{"name": "semantic-config", "prioritizedFields": {"titleField": {"fieldName": "doc_id"}, "contentFields": [{"fieldName": "content"}], "keywordsFields": [{"fieldName": "tags"}]}}]}
# }

# Output search service details
output "search_service_name" {
  value = azurerm_search_service.search.name
}

output "search_service_url" {
  value = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "search_index_name" {
  value = "eng-docs"
}

output "search_service_id" {
  value = azurerm_search_service.search.id
}