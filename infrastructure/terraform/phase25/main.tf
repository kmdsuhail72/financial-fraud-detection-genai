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
# Amazon S3 Bucket for Encrypted KYC Verification Documents (Phase 25)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "kyc_vault" {
  bucket        = "finguard-kyc-documents-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-25"
    Component   = "KYC-Document-Vault"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "kyc_vault_versioning" {
  bucket = aws_s3_bucket.kyc_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kyc_vault_crypto" {
  bucket = aws_s3_bucket.kyc_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Customer Profiles & Onboarding Records
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "kyc_customers" {
  name         = "finguard-kyc-customers-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "onboarding_status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "onboarding_status"
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
    Phase       = "Phase-25"
    Component   = "KYC-Customer-Registry"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Screening Matches (PEP / Sanctions / Adverse Media)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "screening_matches" {
  name         = "finguard-kyc-screening-matches-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "match_id"

  attribute {
    name = "match_id"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  global_secondary_index {
    name            = "CategoryIndex"
    hash_key        = "category"
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
    Phase       = "Phase-25"
    Component   = "Screening-Matches"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Customer Audit Trail Events
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "kyc_audit_trail" {
  name         = "finguard-kyc-audit-trail-${var.environment}"
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
    Phase       = "Phase-25"
    Component   = "Customer-Audit-Trail"
    Environment = var.environment
  }
}

