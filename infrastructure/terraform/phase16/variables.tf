variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS deployment region"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment tier (dev, staging, prod)"
}

variable "vpc_id" {
  type        = string
  default     = "vpc-0123456789abcdef0"
  description = "VPC ID where Neptune and Lambda will be placed"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "VPC CIDR block allowed to communicate with Neptune on port 8182"
}

variable "subnet_ids" {
  type        = list(string)
  default     = ["subnet-0a1b2c3d4e5f0001", "subnet-0a1b2c3d4e5f0002"]
  description = "Subnet IDs across at least 2 Availability Zones for Neptune cluster"
}

variable "kinesis_shard_count" {
  type        = number
  default     = 1
  description = "Number of shards for real-time graph events stream"
}

variable "neptune_engine_version" {
  type        = string
  default     = "1.3.1.0"
  description = "Amazon Neptune engine release version"
}

variable "neptune_instance_class" {
  type        = string
  default     = "db.t3.medium"
  description = "Small development instance class (or db.t4g.medium)"
}

variable "neptune_instance_count" {
  type        = number
  default     = 1
  description = "Number of Neptune cluster reader/writer instances"
}
