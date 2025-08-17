# Application Insights for application monitoring
resource "azurerm_application_insights" "appinsights" {
  name                = "appi-${local.name_prefix}"
  location            = local.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.log.id
  application_type    = "web"
  tags                = local.common_tags
}

# Action Group for alert notifications
resource "azurerm_monitor_action_group" "alerts" {
  name                = "ag-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "ai-alerts"
  tags                = local.common_tags

  # Email notifications for administrators
  dynamic "email_receiver" {
    for_each = var.admin_emails
    content {
      name          = "admin-${email_receiver.key}"
      email_address = email_receiver.value
    }
  }
}

# Alert for high API error rate
resource "azurerm_monitor_metric_alert" "api_error_rate" {
  name                = "api-error-rate-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_container_app.api.id]
  description         = "Alert when API error rate exceeds threshold"
  tags                = local.common_tags

  criteria {
    metric_namespace = "Microsoft.App/containerapps"
    metric_name      = "Requests"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = var.alert_api_error_threshold

    dimension {
      name     = "RevisionName"
      operator = "Include"
      values   = ["*"]
    }

    dimension {
      name     = "StatusCodeCategory" 
      operator = "Include"
      values   = ["5xx"]
    }
  }

  window_size        = "PT5M"
  frequency          = "PT1M"
  severity           = 2
  auto_mitigate      = true

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert for high RAG service latency
resource "azurerm_monitor_metric_alert" "rag_latency" {
  name                = "rag-latency-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_container_app.api.id]
  description         = "Alert when RAG service latency is high"
  tags                = local.common_tags

  criteria {
    metric_namespace = "Microsoft.App/containerapps"
    metric_name      = "RequestDuration"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_rag_latency_threshold_seconds * 1000  # Convert to milliseconds

    dimension {
      name     = "RevisionName"
      operator = "Include"
      values   = ["*"]
    }
  }

  window_size        = "PT5M"
  frequency          = "PT1M"
  severity           = 3
  auto_mitigate      = true

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert for Azure AI Search service availability
resource "azurerm_monitor_metric_alert" "search_availability" {
  name                = "search-availability-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_search_service.search.id]
  description         = "Alert when Azure AI Search service availability drops"
  tags                = local.common_tags

  criteria {
    metric_namespace = "Microsoft.Search/searchServices"
    metric_name      = "SearchLatency"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_search_latency_threshold_seconds * 1000  # Convert to milliseconds
  }

  window_size        = "PT5M"
  frequency          = "PT1M"
  severity           = 2
  auto_mitigate      = true

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert for Azure OpenAI service throttling
resource "azurerm_monitor_metric_alert" "openai_throttling" {
  name                = "openai-throttling-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cognitive_account.openai.id]
  description         = "Alert when Azure OpenAI requests are being throttled"
  tags                = local.common_tags

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "ClientErrors"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = var.alert_openai_error_threshold

    dimension {
      name     = "ErrorType"
      operator = "Include"
      values   = ["RateLimitExceeded", "QuotaExceeded"]
    }
  }

  window_size        = "PT5M"
  frequency          = "PT1M"
  severity           = 2
  auto_mitigate      = true

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert for Cosmos DB high latency (affecting RAG performance)
resource "azurerm_monitor_metric_alert" "cosmos_latency" {
  name                = "cosmos-latency-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cosmosdb_account.main.id]
  description         = "Alert when Cosmos DB latency affects RAG performance"
  tags                = local.common_tags

  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "ServerSideLatency"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_cosmos_latency_threshold_ms
  }

  window_size        = "PT5M"
  frequency          = "PT1M"
  severity           = 3
  auto_mitigate      = true

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Scheduled query alert for AAD authentication failures
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "aad_auth_failures" {
  name                = "aad-auth-failures-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = local.location
  description         = "Alert on AAD authentication failures"
  tags                = local.common_tags

  scopes                = [azurerm_log_analytics_workspace.log.id]
  display_name          = "AAD Authentication Failures"
  enabled               = true
  severity              = 2
  evaluation_frequency  = "PT1M"
  window_duration       = "PT5M"
  auto_mitigation_enabled = true

  criteria {
    query = <<-QUERY
      ContainerAppConsoleLogs_CL
      | where TimeGenerated > ago(5m)
      | where Log_s contains "AAD" and (Log_s contains "failed" or Log_s contains "error" or Log_s contains "unauthorized")
      | where ContainerAppName_s == "api-${local.name_prefix}" or ContainerAppName_s == "web-${local.name_prefix}"
      | summarize count() by bin(TimeGenerated, 1m)
      | where count_ > 0
    QUERY

    time_aggregation_method = "Count"
    threshold               = 1.0
    operator                = "GreaterThanOrEqual"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }
}

# Scheduled query alert for RAG service errors
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "rag_service_errors" {
  name                = "rag-service-errors-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = local.location
  description         = "Alert on RAG service errors and embedding failures"
  tags                = local.common_tags

  scopes                = [azurerm_log_analytics_workspace.log.id]
  display_name          = "RAG Service Errors"
  enabled               = true
  severity              = 2
  evaluation_frequency  = "PT1M"
  window_duration       = "PT10M"
  auto_mitigation_enabled = true

  criteria {
    query = <<-QUERY
      ContainerAppConsoleLogs_CL
      | where TimeGenerated > ago(10m)
      | where Log_s contains "RAG" or Log_s contains "embedding" or Log_s contains "search"
      | where Log_s contains "error" or Log_s contains "failed" or Log_s contains "exception"
      | where ContainerAppName_s == "api-${local.name_prefix}"
      | summarize count() by bin(TimeGenerated, 1m)
      | where count_ > 2
    QUERY

    time_aggregation_method = "Count"
    threshold               = 1.0
    operator                = "GreaterThanOrEqual"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }
}

# Outputs for monitoring resources
output "application_insights_id" {
  description = "ID of Application Insights resource"
  value       = azurerm_application_insights.appinsights.id
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.appinsights.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.appinsights.connection_string
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "ID of Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.log.id
}