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
# Amazon S3 Bucket for Raw and Processed Identity Document Assets (Phase 26)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "identity_doc_store" {
  bucket        = "finguard-identity-docs-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-26"
    Component   = "Identity-Document-Store"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "identity_doc_store_versioning" {
  bucket = aws_s3_bucket.identity_doc_store.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "identity_doc_store_crypto" {
  bucket = aws_s3_bucket.identity_doc_store.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Document Verification Records & Field Consistency
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "doc_verification_records" {
  name         = "finguard-document-verifications-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "verification_id"

  attribute {
    name = "verification_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "CustomerIndex"
    hash_key        = "customer_id"
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
    Phase       = "Phase-26"
    Component   = "Document-Verification-Records"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Document Verification Audit Trail
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "doc_audit_trail" {
  name         = "finguard-doc-verification-audit-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"
  range_key    = "event_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "event_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-26"
    Component   = "Document-Audit-Trail"
    Environment = var.environment
  }
}

