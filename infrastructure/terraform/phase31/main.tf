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
# Amazon S3 Bucket for Raw Banking Ingestion Streams & DLQ Dumps
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "integration_event_archive" {
  bucket        = "finguard-integration-events-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-31"
    Component   = "Integration-Event-Archive"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "integration_event_archive_versioning" {
  bucket = aws_s3_bucket.integration_event_archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "integration_event_archive_crypto" {
  bucket = aws_s3_bucket.integration_event_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Canonical Ingested Events (Idempotency Ledger)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "canonical_events" {
  name         = "finguard-canonical-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  attribute {
    name = "source"
    type = "S"
  }

  attribute {
    name = "received_at"
    type = "S"
  }

  global_secondary_index {
    name            = "IdempotencyIndex"
    hash_key        = "idempotency_key"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "SourceReceivedIndex"
    hash_key        = "source"
    range_key       = "received_at"
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
    Phase       = "Phase-31"
    Component   = "Canonical-Events"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Integration Dead-Letter Queue (DLQ)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "integration_dlq" {
  name         = "finguard-integration-dlq-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "dlq_id"

  attribute {
    name = "dlq_id"
    type = "S"
  }

  attribute {
    name = "failed_at"
    type = "S"
  }

  global_secondary_index {
    name            = "FailedAtIndex"
    hash_key        = "dlq_id"
    range_key       = "failed_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-31"
    Component   = "Integration-DLQ"
    Environment = var.environment
  }
}
