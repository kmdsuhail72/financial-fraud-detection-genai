# ==============================================================================
# FinGuard AI — Phase 40: Terraform Variables
# ==============================================================================

variable "aws_region" {
  description = "Target AWS region for messaging infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Target environment name"
  type        = string
  default     = "production"
}

variable "max_receive_count" {
  description = "Maximum attempts before message is quarantined to Dead-Letter Queue (DLQ)"
  type        = number
  default     = 3
}
