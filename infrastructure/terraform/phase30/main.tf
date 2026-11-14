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
# Amazon S3 Bucket for Regulatory Filing Dossiers & Evidence Bundles
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "regulatory_filing_vault" {
  bucket        = "finguard-regulatory-filings-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-30"
    Component   = "Regulatory-Reporting-Vault"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "regulatory_filing_vault_versioning" {
  bucket = aws_s3_bucket.regulatory_filing_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "regulatory_filing_vault_crypto" {
  bucket = aws_s3_bucket.regulatory_filing_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Regulatory SAR/STR Reports
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "regulatory_reports" {
  name         = "finguard-regulatory-reports-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "report_id"

  attribute {
    name = "report_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "CustomerIdIndex"
    hash_key        = "customer_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "created_at"
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
    Phase       = "Phase-30"
    Component   = "Regulatory-Reports"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Regulatory Audit Events
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "regulatory_audit_events" {
  name         = "finguard-regulatory-audit-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "report_id"
  range_key    = "event_id"

  attribute {
    name = "report_id"
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
    Phase       = "Phase-30"
    Component   = "Regulatory-Audit-Trail"
    Environment = var.environment
  }
}
