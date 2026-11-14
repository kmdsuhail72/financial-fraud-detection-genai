# ==============================================================================
# FinGuard AI — Phase 39: Terraform Variables
# ==============================================================================

variable "aws_region" {
  description = "Target AWS region for ElastiCache deployment"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "vpc_id" {
  description = "Target VPC ID"
  type        = string
  default     = "vpc-0f72a6b18c9d41234"
}

variable "app_vpc_cidr" {
  description = "CIDR block permitted to access the Redis cluster"
  type        = string
  default     = "10.0.0.0/16"
}

variable "cache_subnet_ids" {
  description = "Subnet IDs spanning distinct Availability Zones"
  type        = list(string)
  default     = ["subnet-0a1b2c3d4e5f6001", "subnet-0a1b2c3d4e5f6002"]
}

variable "node_type" {
  description = "ElastiCache node instance type"
  type        = string
  default     = "cache.t4g.medium"
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (1 Primary + (N-1) Replicas)"
  type        = number
  default     = 2
}

variable "auth_token" {
  description = "Auth token (password) for Redis AUTH; min 16 characters"
  type        = string
  default     = "FinGuardProdSecureToken2026!"
  sensitive   = true
}
