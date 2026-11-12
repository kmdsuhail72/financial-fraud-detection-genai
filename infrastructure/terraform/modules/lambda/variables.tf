variable "project_name" {
  type    = string
  default = "finguard"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "kinesis_stream_arn" {
  type = string
}

variable "processed_bucket_name" {
  type = string
}

variable "processed_bucket_arn" {
  type = string
}

variable "idempotency_table_name" {
  type = string
}

variable "idempotency_table_arn" {
  type = string
}

variable "customer_state_table_name" {
  type = string
}

variable "customer_state_table_arn" {
  type = string
}

variable "sqs_quarantine_url" {
  type = string
}

variable "sqs_quarantine_arn" {
  type = string
}
