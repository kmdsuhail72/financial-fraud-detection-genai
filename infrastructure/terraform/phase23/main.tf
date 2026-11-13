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
# Amazon S3 Bucket for Regulatory Compliance & Audit Reports (Phase 23)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "compliance_reports" {
  bucket        = "finguard-compliance-reports-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-23"
    Component   = "Regulatory-Compliance-Reports"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "compliance_versioning" {
  bucket = aws_s3_bucket.compliance_reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "compliance_crypto" {
  bucket = aws_s3_bucket.compliance_reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Regulatory Governance Controls
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "governance_controls" {
  name         = "finguard-governance-controls-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "control_id"

  attribute {
    name = "control_id"
    type = "S"
  }

  attribute {
    name = "domain"
    type = "S"
  }

  attribute {
    name = "effectiveness"
    type = "S"
  }

  global_secondary_index {
    name            = "domain-effectiveness-index"
    hash_key        = "domain"
    range_key       = "effectiveness"
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
    Phase       = "Phase-23"
    Component   = "Governance-Control-Catalogue"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Compliance Findings & Deficiencies
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "governance_findings" {
  name         = "finguard-governance-findings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "finding_id"

  attribute {
    name = "finding_id"
    type = "S"
  }

  attribute {
    name = "control_id"
    type = "S"
  }

  attribute {
    name = "severity"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "control-findings-index"
    hash_key        = "control_id"
    range_key       = "status"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "severity-status-index"
    hash_key        = "severity"
    range_key       = "status"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-23"
    Component   = "Governance-Findings-Registry"
    Environment = var.environment
  }
}

