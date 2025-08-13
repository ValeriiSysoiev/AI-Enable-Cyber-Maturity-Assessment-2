locals { sa_name_prefix = replace(local.name_prefix, "-", "") }

resource "random_string" "sa" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}

resource "azurerm_storage_account" "sa" {
  name                            = substr("st${local.sa_name_prefix}${random_string.sa.result}", 0, 24)
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = local.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  tags                            = local.common_tags
}

resource "azurerm_storage_container" "docs" {
  name                  = "docs"
  storage_account_id    = azurerm_storage_account.sa.id
  container_access_type = "private"
}

output "storage_account_name" {
  value = azurerm_storage_account.sa.name
}
output "docs_container_url" {
  value = "${azurerm_storage_account.sa.primary_blob_endpoint}docs"
}
