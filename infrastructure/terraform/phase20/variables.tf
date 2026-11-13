variable "aws_region" {
  description = "AWS deployment region."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment target environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

