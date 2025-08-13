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

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}
output "key_vault_uri" {
  value = azurerm_key_vault.kv.vault_uri
}
