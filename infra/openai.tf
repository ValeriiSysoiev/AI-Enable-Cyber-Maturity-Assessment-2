# Azure OpenAI Service for Embeddings
resource "azurerm_cognitive_account" "openai" {
  name                = "openai-${local.name_prefix}"
  location            = var.openai_location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"

  # Disable public network access for security
  public_network_access_enabled = false
  
  # Custom subdomain is required for OpenAI
  custom_subdomain_name = "openai-${replace(local.name_prefix, "-", "")}"
  
  tags = local.common_tags
}

# Embedding model deployment for text-embedding-3-large
resource "azurerm_cognitive_deployment" "text_embedding_3_large" {
  name                 = "text-embedding-3-large"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }
  
  sku {
    name     = "Standard"
    capacity = 1
  }
}

# Output OpenAI service details
output "openai_service_name" {
  value = azurerm_cognitive_account.openai.name
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_service_id" {
  value = azurerm_cognitive_account.openai.id
}

output "embedding_deployment_name" {
  value = azurerm_cognitive_deployment.text_embedding_3_large.name
}