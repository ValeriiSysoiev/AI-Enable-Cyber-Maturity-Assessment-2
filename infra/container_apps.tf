# Container App for API service
resource "azurerm_container_app" "api" {
  name                         = "api-${local.name_prefix}"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  # Template configuration
  template {
    min_replicas = 1
    max_replicas = 3

    # API container configuration
    container {
      name   = "api"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"  # Placeholder - replaced by deployment scripts
      cpu    = "0.25"
      memory = "0.5Gi"

      # Environment variables for RAG and AAD functionality
      env {
        name  = "AUTH_MODE"
        value = var.auth_mode
      }

      env {
        name  = "RAG_MODE"
        value = var.rag_mode
      }

      env {
        name  = "EMBED_MODEL"
        value = var.embed_model
      }

      env {
        name = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = azurerm_cognitive_deployment.text_embedding_3_large.name
      }

      env {
        name = "AZURE_SEARCH_ENDPOINT"
        value = "https://${azurerm_search_service.search.name}.search.windows.net"
      }

      env {
        name = "AZURE_SEARCH_INDEX_NAME"
        value = "eng-docs"
      }

      env {
        name = "COSMOS_ENDPOINT"
        value = azurerm_cosmosdb_account.main.endpoint
      }

      env {
        name = "COSMOS_DATABASE_NAME"
        value = azurerm_cosmosdb_sql_database.main.name
      }

      env {
        name = "RAG_COSMOS_CONTAINER"
        value = azurerm_cosmosdb_sql_container.embeddings.name
      }

      env {
        name = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.sa.name
      }

      env {
        name = "AZURE_STORAGE_CONTAINER"
        value = "docs"
      }

      env {
        name = "USE_MANAGED_IDENTITY"
        value = "true"
      }

      env {
        name = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api.client_id
      }

      env {
        name = "KEY_VAULT_URI"
        value = azurerm_key_vault.kv.vault_uri
      }

      # Logging configuration
      env {
        name = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name = "LOG_FORMAT"
        value = "json"
      }

      # RAG specific configuration
      env {
        name = "RAG_SEARCH_TOP_K"
        value = tostring(var.rag_search_top_k)
      }

      env {
        name = "RAG_SIMILARITY_THRESHOLD"
        value = tostring(var.rag_similarity_threshold)
      }

      env {
        name = "RAG_USE_HYBRID_SEARCH"
        value = tostring(var.rag_use_hybrid_search)
      }

      env {
        name = "RAG_FEATURE_FLAG"
        value = tostring(var.rag_feature_flag_enabled)
      }

      # Security headers
      env {
        name = "ALLOWED_ORIGINS"
        value = join(",", var.api_allowed_origins)
      }
    }

    # HTTP scale rule
    http_scale_rule {
      name                = "http-scale"
      concurrent_requests = 30
    }
  }

  # Managed identity configuration
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  # Ingress configuration
  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8000
    transport                  = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Secret configuration for Key Vault access
  secret {
    name  = "azure-client-id"
    value = azurerm_user_assigned_identity.api.client_id
  }

  depends_on = [
    azurerm_user_assigned_identity.api,
    azurerm_cosmosdb_sql_role_assignment.api_cosmos_contributor,
    azurerm_role_assignment.api_kv_secrets_user,
    azurerm_role_assignment.api_search_service_contributor,
    azurerm_role_assignment.api_openai_user
  ]
}

# Container App for Web service  
resource "azurerm_container_app" "web" {
  name                         = "web-${local.name_prefix}"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "web"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"  # Placeholder - replaced by deployment scripts
      cpu    = "0.25"
      memory = "0.5Gi"

      # Environment variables for authentication
      env {
        name = "AUTH_MODE"
        value = var.auth_mode
      }

      env {
        name = "API_BASE_URL"
        value = "https://${azurerm_container_app.api.latest_revision_fqdn}"
      }

      env {
        name = "NEXTAUTH_URL"
        value = "https://web-${local.name_prefix}.${azurerm_container_app_environment.env.default_domain}"
      }

      env {
        name = "KEY_VAULT_URI"
        value = azurerm_key_vault.kv.vault_uri
      }

      env {
        name = "USE_MANAGED_IDENTITY"
        value = "true"
      }

      env {
        name = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.web.client_id
      }
    }

    http_scale_rule {
      name                = "http-scale"
      concurrent_requests = 50
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.web.id]
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 3000
    transport                  = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    azurerm_container_app.api,
    azurerm_user_assigned_identity.web
  ]
}

# Outputs for application URLs
output "api_url" {
  description = "URL of the API container app"
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
}

output "web_url" {
  description = "URL of the Web container app"
  value       = "https://${azurerm_container_app.web.latest_revision_fqdn}"
}

output "api_app_name" {
  description = "Name of the API container app"
  value       = azurerm_container_app.api.name
}

output "web_app_name" {
  description = "Name of the Web container app"
  value       = azurerm_container_app.web.name
}