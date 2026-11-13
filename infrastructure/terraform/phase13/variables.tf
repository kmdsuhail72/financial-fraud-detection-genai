variable "aws_region" {
  type        = string
  default     = "ap-south-1"
  description = "AWS region for FinGuard AI threat intelligence infrastructure."
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment (e.g. production, staging)."
}

variable "retention_days" {
  type        = number
  default     = 365
  description = "Threat intelligence telemetry archive retention period in days."
}
