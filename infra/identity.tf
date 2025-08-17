resource "azurerm_user_assigned_identity" "api" {
  name                = "uai-api-${local.name_prefix}"
  location            = local.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

resource "azurerm_user_assigned_identity" "web" {
  name                = "uai-web-${local.name_prefix}"
  location            = local.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

# API identity can pull from ACR
resource "azurerm_role_assignment" "api_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# Web identity can pull from ACR
resource "azurerm_role_assignment" "web_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.web.principal_id
}

# API identity can generate user-delegation SAS on Storage (write/create)
resource "azurerm_role_assignment" "api_storage_blob_contrib" {
  scope                = azurerm_storage_account.sa.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can read secrets from Key Vault (future use)
resource "azurerm_role_assignment" "api_kv_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can query Azure AI Search
resource "azurerm_role_assignment" "api_search_service_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Service Contributor"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can use Azure AI Search indexes
resource "azurerm_role_assignment" "api_search_index_data_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can read from Azure AI Search
resource "azurerm_role_assignment" "api_search_index_data_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can use Azure OpenAI
resource "azurerm_role_assignment" "api_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# API identity can contribute to Azure OpenAI (for monitoring/logging)
resource "azurerm_role_assignment" "api_openai_contributor" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI Contributor"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

output "uai_api_principal_id" { value = azurerm_user_assigned_identity.api.principal_id }
output "uai_web_principal_id" { value = azurerm_user_assigned_identity.web.principal_id }
output "uai_api_id" { value = azurerm_user_assigned_identity.api.id }
output "uai_web_id" { value = azurerm_user_assigned_identity.web.id }




