provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "FinGuard AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "s3" {
  source       = "../../modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "kinesis" {
  source       = "../../modules/kinesis"
  project_name = var.project_name
  environment  = var.environment
}

module "dynamodb" {
  source       = "../../modules/dynamodb"
  project_name = var.project_name
  environment  = var.environment
}

module "sqs" {
  source       = "../../modules/sqs"
  project_name = var.project_name
  environment  = var.environment
}

module "lambda" {
  source                    = "../../modules/lambda"
  project_name              = var.project_name
  environment               = var.environment
  aws_region                = var.aws_region
  kinesis_stream_arn        = module.kinesis.stream_arn
  processed_bucket_name     = var.processed_bucket_name
  processed_bucket_arn      = module.s3.bucket_arn
  idempotency_table_name    = module.dynamodb.idempotency_table_name
  idempotency_table_arn     = module.dynamodb.idempotency_table_arn
  customer_state_table_name = module.dynamodb.customer_state_table_name
  customer_state_table_arn  = module.dynamodb.customer_state_table_arn
  sqs_quarantine_url        = module.sqs.queue_url
  sqs_quarantine_arn        = module.sqs.queue_arn
}
