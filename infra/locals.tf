locals {
  # e.g., "aaa-demo"
  name_prefix = lower("${var.client_code}-${var.env}")
  location    = var.location

  # Merge defaults with per-deploy values
  common_tags = merge(
    var.tags,
    {
      Client      = var.client_code
      Environment = var.env
    }
  )
}
