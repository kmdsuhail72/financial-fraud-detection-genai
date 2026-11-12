variable "aws_region" {
  description = "AWS region for FinGuard deployment"
  type        = string
  default     = "ap-south-1"
}

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

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID or inference profile for investigation assistant"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20240620-v1:0"
}

variable "investigation_alerts_queue_arn" {
  description = "Phase 7 SQS Investigation Alerts Queue ARN"
  type        = string
  default     = "arn:aws:sqs:ap-south-1:123456789012:finguard-investigation-alerts-dev"
}
