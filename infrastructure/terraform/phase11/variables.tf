variable "aws_region" {
  description = "AWS deployment region."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix."
  type        = string
  default     = "finguard"
}

variable "enable_guardduty" {
  description = "Whether to provision Amazon GuardDuty detector (disabled by default to prevent unexpected AWS cost)."
  type        = bool
  default     = false
}

variable "enable_security_hub" {
  description = "Whether to provision AWS Security Hub standard (disabled by default to prevent unexpected AWS cost)."
  type        = bool
  default     = false
}

variable "security_alerts_email" {
  description = "Optional email address to receive high-severity SNS security notifications."
  type        = string
  default     = "security-ops@finguard.internal"
}

