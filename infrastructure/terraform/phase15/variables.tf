variable "aws_region" {
  type        = string
  default     = "ap-south-1"
  description = "AWS region for FinGuard AI graph infrastructure."
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment (e.g. production, staging)."
}

variable "vpc_id" {
  type        = string
  default     = "vpc-0123456789abcdef0"
  description = "VPC ID where Neptune cluster will reside."
}

variable "subnet_ids" {
  type        = list(string)
  default     = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
  description = "Subnet IDs for the Neptune DB subnet group."
}

variable "neptune_instance_class" {
  type        = string
  default     = "db.r5.large"
  description = "Neptune DB instance type."
}

variable "backup_retention_period" {
  type        = number
  default     = 7
  description = "Automated backup retention days."
}

variable "enable_iam_database_authentication" {
  type        = bool
  default     = true
  description = "Enforce SigV4 IAM authentication for Neptune connections."
}

