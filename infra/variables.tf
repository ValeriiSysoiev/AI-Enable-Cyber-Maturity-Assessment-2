variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "location" {
  description = "Azure region (Canada)"
  type        = string
  default     = "canadacentral"
}

variable "env" {
  description = "Environment name (e.g., demo, dev, prod)"
  type        = string
  default     = "demo"
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default = {
    Project     = "AI-Enable-Cyber-Maturity-Assessment"
    Environment = "demo"
    Owner       = "valsysoiev"
  }
}

variable "client_code" {
  description = "Short code for the client (e.g., AAA)"
  type        = string
  default     = "AAA"
}

variable "search_service_tier" {
  description = "Azure AI Search service tier (basic, standard, standard2, standard3, storage_optimized_l1, storage_optimized_l2)"
  type        = string
  default     = "standard"
  validation {
    condition = contains(["basic", "standard", "standard2", "standard3", "storage_optimized_l1", "storage_optimized_l2"], var.search_service_tier)
    error_message = "Search service tier must be one of: basic, standard, standard2, standard3, storage_optimized_l1, storage_optimized_l2."
  }
}

variable "search_replica_count" {
  description = "Number of search service replicas"
  type        = number
  default     = 1
  validation {
    condition = var.search_replica_count >= 1 && var.search_replica_count <= 12
    error_message = "Replica count must be between 1 and 12."
  }
}

variable "search_partition_count" {
  description = "Number of search service partitions"
  type        = number
  default     = 1
  validation {
    condition = contains([1, 2, 3, 4, 6, 12], var.search_partition_count)
    error_message = "Partition count must be one of: 1, 2, 3, 4, 6, 12."
  }
}

variable "openai_location" {
  description = "Azure region for OpenAI service (limited availability)"
  type        = string
  default     = "canadaeast"
}

# RAG Configuration Variables
variable "rag_mode" {
  description = "RAG mode (none, azure_openai)"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "azure_openai"], var.rag_mode)
    error_message = "RAG mode must be 'none' or 'azure_openai'."
  }
}

variable "embed_model" {
  description = "Embedding model to use for RAG"
  type        = string
  default     = "text-embedding-3-large"
}

variable "rag_search_top_k" {
  description = "Number of top search results for RAG"
  type        = number
  default     = 10
  validation {
    condition     = var.rag_search_top_k >= 1 && var.rag_search_top_k <= 50
    error_message = "RAG search top K must be between 1 and 50."
  }
}

variable "rag_similarity_threshold" {
  description = "Similarity threshold for RAG search results"
  type        = number
  default     = 0.7
  validation {
    condition     = var.rag_similarity_threshold >= 0.0 && var.rag_similarity_threshold <= 1.0
    error_message = "RAG similarity threshold must be between 0.0 and 1.0."
  }
}

variable "rag_use_hybrid_search" {
  description = "Enable hybrid search for RAG (vector + keyword)"
  type        = bool
  default     = true
}

variable "rag_feature_flag_enabled" {
  description = "Enable RAG feature flag for gradual rollout"
  type        = bool
  default     = true
}

# Authentication Configuration Variables
variable "auth_mode" {
  description = "Authentication mode (demo, aad)"
  type        = string
  default     = "demo"
  validation {
    condition     = contains(["demo", "aad"], var.auth_mode)
    error_message = "Auth mode must be 'demo' or 'aad'."
  }
}

# Application Configuration Variables
variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

variable "api_allowed_origins" {
  description = "Allowed CORS origins for API"
  type        = list(string)
  default     = ["*"]
}

variable "admin_emails" {
  description = "List of admin email addresses for alerts"
  type        = list(string)
  default     = []
}

# Monitoring and Alerting Thresholds - Optimized for Performance
variable "alert_api_error_threshold" {
  description = "Threshold for API error rate alerts (count per 5 minutes)"
  type        = number
  default     = 15  # Increased to reduce false positives with higher traffic
}

variable "alert_rag_latency_threshold_seconds" {
  description = "Threshold for RAG service latency alerts (seconds)"
  type        = number
  default     = 8   # Reduced for better user experience with optimized resources
}

variable "alert_search_latency_threshold_seconds" {
  description = "Threshold for search service latency alerts (seconds)"
  type        = number
  default     = 2   # Tightened for better search performance
}

variable "alert_openai_error_threshold" {
  description = "Threshold for OpenAI service error alerts (count per 5 minutes)"
  type        = number
  default     = 8   # Increased for better tolerance with higher throughput
}

variable "alert_cosmos_latency_threshold_ms" {
  description = "Threshold for Cosmos DB latency alerts (milliseconds)"
  type        = number
  default     = 150  # Increased slightly for better tolerance with concurrent operations
}

# Additional Performance Monitoring Variables
variable "alert_container_cpu_threshold" {
  description = "CPU utilization threshold for container scaling alerts (%)"
  type        = number
  default     = 70
}

variable "alert_container_memory_threshold" {
  description = "Memory utilization threshold for container scaling alerts (%)"
  type        = number
  default     = 80
}

variable "alert_http_response_time_threshold" {
  description = "HTTP response time threshold for performance alerts (seconds)"
  type        = number
  default     = 3
}
