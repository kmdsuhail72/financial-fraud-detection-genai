variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS deployment region."
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Deployment target environment (dev, staging, prod)."
}

