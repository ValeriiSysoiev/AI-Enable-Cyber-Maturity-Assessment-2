# Azure Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${local.name_prefix}"
  location            = local.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  automatic_failover_enabled = false
  free_tier_enabled          = false

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = local.location
    failover_priority = 0
  }

  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Geo"
  }

  tags = local.common_tags
}

# Azure Cosmos DB SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "ai_maturity"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Cosmos DB Containers
resource "azurerm_cosmosdb_sql_container" "assessments" {
  name                  = "assessments"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "answers" {
  name                  = "answers"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "documents" {
  name                  = "documents"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "engagements" {
  name                  = "engagements"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "findings" {
  name                  = "findings"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "memberships" {
  name                  = "memberships"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "recommendations" {
  name                  = "recommendations"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "runlogs" {
  name                  = "runlogs"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
}

resource "azurerm_cosmosdb_sql_container" "embeddings" {
  name                  = "embeddings"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/engagement_id"]
  partition_key_kind    = "Hash"
  
  # Optimize for RAG vector storage and retrieval
  default_ttl = -1  # No automatic expiration
  
  # Configure indexing policy for vector operations
  indexing_policy {
    indexing_mode = "consistent"
    
    # Include paths for efficient querying
    included_path {
      path = "/*"
    }
    
    # Exclude vector embeddings from indexing to save storage
    excluded_path {
      path = "/embedding_vector/*"
    }
    
    # Optimize for common RAG query patterns
    excluded_path {
      path = "/content_vector/*"
    }
  }
}

# Built-in Cosmos DB Data Contributor role for API
data "azurerm_cosmosdb_sql_role_definition" "contributor" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "00000000-0000-0000-0000-000000000002"
}

# Role assignment for API managed identity
resource "azurerm_cosmosdb_sql_role_assignment" "api_cosmos_contributor" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = data.azurerm_cosmosdb_sql_role_definition.contributor.id
  principal_id        = azurerm_user_assigned_identity.api.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Store connection string in Key Vault
resource "azurerm_key_vault_secret" "cosmos_connstr" {
  name         = "cosmos-connstr"
  value        = azurerm_cosmosdb_account.main.primary_sql_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.common_tags
}

# Output Cosmos DB details
output "cosmos_account_name" {
  value = azurerm_cosmosdb_account.main.name
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "cosmos_database_name" {
  value = azurerm_cosmosdb_sql_database.main.name
}

output "cosmos_primary_key" {
  value     = azurerm_cosmosdb_account.main.primary_key
  sensitive = true
}