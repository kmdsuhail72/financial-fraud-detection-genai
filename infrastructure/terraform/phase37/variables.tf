# Variables for FinGuard AI Phase 37 Disaster Recovery
variable "primary_region" {
  description = "Primary AWS region for FinGuard production workloads"
  type        = string
  default     = "ap-south-1" # Mumbai
}

variable "secondary_region" {
  description = "Secondary disaster-recovery AWS region"
  type        = string
  default     = "ap-southeast-1" # Singapore
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "bucket_prefix" {
  description = "S3 bucket naming prefix"
  type        = string
  default     = "finguard-evidence-lake"
}

