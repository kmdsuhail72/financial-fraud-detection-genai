terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# Amazon S3 Bucket for Payment Event Streaming & Historical Gateway Lake
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "payment_event_lake" {
  bucket        = "finguard-payment-events-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-29"
    Component   = "Payment-Event-Lake"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "payment_event_lake_versioning" {
  bucket = aws_s3_bucket.payment_event_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "payment_event_lake_crypto" {
  bucket = aws_s3_bucket.payment_event_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Real-Time Payment Risk Assessments
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "payment_assessments" {
  name         = "finguard-payment-assessments-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "assessed_at"
    type = "S"
  }

  global_secondary_index {
    name            = "CustomerIdIndex"
    hash_key        = "customer_id"
    range_key       = "assessed_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-29"
    Component   = "Payment-Assessments"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Payment Velocity & Rate Limiting Window
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "payment_velocity_window" {
  name         = "finguard-payment-velocity-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"
  range_key    = "timestamp"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-29"
    Component   = "Payment-Velocity"
    Environment = var.environment
  }
}
