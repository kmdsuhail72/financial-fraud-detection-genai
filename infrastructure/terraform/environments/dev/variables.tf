variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "finguard"
}

variable "processed_bucket_name" {
  description = "Globally unique bucket name for processed transaction storage"
  type        = string
  default     = "finguard-data-processed-dev"
}
