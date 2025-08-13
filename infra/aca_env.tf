resource "random_string" "log" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}

resource "azurerm_log_analytics_workspace" "log" {
  name                = "log-${replace(local.name_prefix,"-","")}-${random_string.log.result}"
  location            = local.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_container_app_environment" "env" {
  name                       = "aca-${local.name_prefix}"
  location                   = local.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log.id
  tags                       = local.common_tags
}

output "aca_env_name" { value = azurerm_container_app_environment.env.name }
