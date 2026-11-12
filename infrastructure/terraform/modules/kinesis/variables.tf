variable "project_name" {
  description = "Project identifier"
  type        = string
  default     = "finguard"
}

variable "environment" {
  description = "Target deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "retention_period_hours" {
  description = "Stream retention period in hours (24 to 8760)"
  type        = number
  default     = 24
}

variable "stream_mode" {
  description = "Kinesis stream mode: ON_DEMAND or PROVISIONED"
  type        = string
  default     = "ON_DEMAND"
}

variable "shard_count" {
  description = "Number of provisioned shards (if stream_mode is PROVISIONED)"
  type        = number
  default     = 2
}

variable "kms_key_arn" {
  description = "Optional KMS key ARN for server-side encryption"
  type        = string
  default     = "aws/kinesis"
}

