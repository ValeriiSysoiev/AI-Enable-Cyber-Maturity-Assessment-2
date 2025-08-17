locals { kv_name_prefix = replace(local.name_prefix, "-", "") }

resource "random_string" "kv" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                          = substr("kv${local.kv_name_prefix}${random_string.kv.result}", 0, 24)
  location                      = local.location
  resource_group_name           = azurerm_resource_group.rg.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  soft_delete_retention_days    = 7
  purge_protection_enabled      = true
  public_network_access_enabled = true
  tags                          = local.common_tags
}

# Store Azure AI Search admin key in Key Vault
resource "azurerm_key_vault_secret" "search_admin_key" {
  name         = "search-admin-key"
  value        = azurerm_search_service.search.primary_key
  key_vault_id = azurerm_key_vault.kv.id
  
  depends_on = [azurerm_search_service.search]
  
  tags = local.common_tags
}

# Store Azure OpenAI key in Key Vault
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.kv.id
  
  depends_on = [azurerm_cognitive_account.openai]
  
  tags = local.common_tags
}

# AAD Application secrets (placeholders - actual values set during AAD configuration)
resource "azurerm_key_vault_secret" "aad_client_id" {
  name         = "aad-client-id"
  value        = "placeholder-client-id"
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.common_tags
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "aad_client_secret" {
  name         = "aad-client-secret"
  value        = "placeholder-client-secret"
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.common_tags
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "aad-tenant-id"
  value        = var.tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.common_tags
}

# NextAuth secret for session encryption
resource "azurerm_key_vault_secret" "nextauth_secret" {
  name         = "nextauth-secret"
  value        = "placeholder-nextauth-secret"
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.common_tags
  
  lifecycle {
    ignore_changes = [value]
  }
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}
output "key_vault_uri" {
  value = azurerm_key_vault.kv.vault_uri
}
