# Variables for FinGuard AI Phase 36 Observability
variable "aws_region" {
  description = "AWS deployment region (default: AWS Mumbai ap-south-1)"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Target deployment environment (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "EKS Cluster Name"
  type        = string
  default     = "finguard-eks-mumbai"
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 90
}

