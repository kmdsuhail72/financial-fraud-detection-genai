variable "aws_region" {
  description = "AWS deployment region."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment stage identifier (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix."
  type        = string
  default     = "finguard"
}

variable "audit_table_name" {
  description = "DynamoDB table for immutable security audit logging."
  type        = string
  default     = "finguard-dev-security-audit"
}

variable "callback_urls" {
  description = "Permitted OIDC OAuth redirect URIs for React SPA."
  type        = list(string)
  default     = [
    "http://localhost:5173",
    "http://localhost:5173/callback",
    "http://localhost:80/callback",
    "https://finguard.internal/callback"
  ]
}

variable "logout_urls" {
  description = "Permitted signout redirect URIs."
  type        = list(string)
  default     = [
    "http://localhost:5173/login",
    "http://localhost:80/login",
    "https://finguard.internal/login"
  ]
}

