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
# Amazon S3 Bucket for SAR Investigation Drafts (Phase 24)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "sar_vault" {
  bucket        = "finguard-aml-sar-drafts-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-24"
    Component   = "AML-SAR-Vault"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "sar_vault_versioning" {
  bucket = aws_s3_bucket.sar_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sar_vault_crypto" {
  bucket = aws_s3_bucket.sar_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for AML Investigation Cases
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "aml_cases" {
  name         = "finguard-aml-cases-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "case_id"

  attribute {
    name = "case_id"
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
    name = "risk_tier"
    type = "S"
  }

  global_secondary_index {
    name            = "customer-cases-index"
    hash_key        = "customer_id"
    range_key       = "status"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-risk-index"
    hash_key        = "status"
    range_key       = "risk_tier"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-24"
    Component   = "AML-Cases-Registry"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Customer Risk Profiles
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "customer_risk_profiles" {
  name         = "finguard-customer-risk-profiles-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "risk_tier"
    type = "S"
  }

  global_secondary_index {
    name            = "risk-tier-index"
    hash_key        = "risk_tier"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-24"
    Component   = "AML-Customer-Risk-Profiles"
    Environment = var.environment
  }
}

