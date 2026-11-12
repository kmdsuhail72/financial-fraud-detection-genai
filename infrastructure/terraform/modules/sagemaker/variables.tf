variable "environment" {
  description = "Target environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "finguard"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "model_bucket_name" {
  description = "S3 bucket name for SageMaker model artifacts"
  type        = string
  default     = "finguard-ml-models-dev"
}

variable "enable_realtime_endpoint" {
  description = "Whether to provision an active SageMaker real-time endpoint (incurs hourly compute charges)"
  type        = bool
  default     = false
}

variable "instance_type" {
  description = "EC2 instance type for SageMaker endpoint"
  type        = string
  default     = "ml.m5.large"
}
