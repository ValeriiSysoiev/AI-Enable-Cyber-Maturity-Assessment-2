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
