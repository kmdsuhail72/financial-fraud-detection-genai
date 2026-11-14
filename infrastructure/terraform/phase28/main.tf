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
# Amazon S3 Bucket for Unified Customer Risk Intelligence Dossiers & Reports
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "risk_dossier_vault" {
  bucket        = "finguard-customer-risk-dossiers-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-28"
    Component   = "Customer-Risk-Dossiers"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "risk_dossier_vault_versioning" {
  bucket = aws_s3_bucket.risk_dossier_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "risk_dossier_vault_crypto" {
  bucket = aws_s3_bucket.risk_dossier_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Unified Customer Risk Assessments
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "customer_risk_assessments" {
  name         = "finguard-customer-risk-assessments-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "assessment_id"

  attribute {
    name = "assessment_id"
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
    Phase       = "Phase-28"
    Component   = "Customer-Risk-Assessments"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Customer Continuous Reassessment History
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "customer_risk_history" {
  name         = "finguard-customer-risk-history-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"
  range_key    = "assessment_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "assessment_id"
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
    Phase       = "Phase-28"
    Component   = "Customer-Risk-History"
    Environment = var.environment
  }
}

