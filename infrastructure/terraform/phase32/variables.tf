variable "aws_region" {
  description = "AWS region for API Gateway and CloudWatch"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment (e.g. staging, prod, dev)"
  type        = string
  default     = "production"
}

variable "allowed_origins" {
  description = "Allowed origins for API Gateway CORS"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:5173", "https://app.finguard.internal"]
}

variable "throttling_burst_limit" {
  description = "Throttling burst limit for default route"
  type        = number
  default     = 100
}

variable "throttling_rate_limit" {
  description = "Throttling steady rate limit (requests per second)"
  type        = number
  default     = 50
}

