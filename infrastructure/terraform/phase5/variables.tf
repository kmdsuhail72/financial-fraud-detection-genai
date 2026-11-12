variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "finguard"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "data_lake_bucket_name" {
  type        = string
  description = "Globally unique bucket name for FinGuard AI Medallion Data Lake"
}
