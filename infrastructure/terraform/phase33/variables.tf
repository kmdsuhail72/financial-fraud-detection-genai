variable "aws_region" {
  description = "AWS region for event infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "max_receive_count" {
  description = "Number of retry attempts before message is routed to DLQ"
  type        = number
  default     = 3
}
