resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name_prefix}"
  location = local.location
  tags     = local.common_tags
}

output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}
