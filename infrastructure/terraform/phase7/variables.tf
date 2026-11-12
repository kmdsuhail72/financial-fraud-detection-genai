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

variable "artifact_bucket_name" {
  description = "Your Phase 6 artifact bucket storing model.tar.gz"
  type        = string
  default     = "finguard-ml-models-dev"
}

variable "model_data_url" {
  description = "S3 URI to uploaded model.tar.gz (e.g. s3://bucket/models/finguard/v1/model.tar.gz)"
  type        = string
  default     = "s3://finguard-ml-models-dev/models/finguard/v1/model.tar.gz"
}

variable "sagemaker_image_uri" {
  description = "Compatible SageMaker scikit-learn / XGBoost inference image URI"
  type        = string
  default     = "720646828776.dkr.ecr.ap-south-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"
}

variable "kinesis_stream_arn" {
  description = "Phase 3 Kinesis Data Stream ARN"
  type        = string
  default     = "arn:aws:kinesis:ap-south-1:123456789012:stream/finguard-transactions-dev"
}

variable "model_feature_columns_json" {
  description = "Exact feature columns from Phase 6 manifest as JSON string"
  type        = string
  default     = "[\"transaction_amount\",\"avg_amount_24h\",\"transaction_count_5m\",\"transaction_count_1h\",\"amount_deviation\",\"new_device\",\"location_change\",\"international_flag\",\"merchant_risk\",\"account_age_days\"]"
}

variable "enable_sagemaker_endpoint" {
  description = "Whether to provision an active SageMaker real-time endpoint (incurs continuous hourly EC2 instance charges)"
  type        = bool
  default     = false
}

variable "sagemaker_instance_type" {
  description = "Instance type for real-time SageMaker endpoint"
  type        = string
  default     = "ml.m5.large"
}
