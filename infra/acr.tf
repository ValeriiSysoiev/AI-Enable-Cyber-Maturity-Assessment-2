locals { acr_name_prefix = replace(local.name_prefix, "-", "") }

resource "random_string" "acr" {
  length = 6
  upper = false
  lower = true
  numeric = true
  special = false
}

resource "azurerm_container_registry" "acr" {
  name                = "acr${local.acr_name_prefix}${random_string.acr.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = local.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.common_tags
}

output "acr_name"         { value = azurerm_container_registry.acr.name }
output "acr_login_server" { value = azurerm_container_registry.acr.login_server }
