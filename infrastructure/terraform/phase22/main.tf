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
# Amazon S3 Digital Evidence Vault with Object Lock & Versioning (Phase 22)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "evidence_vault" {
  bucket        = "finguard-evidence-vault-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-22"
    Component   = "Forensics-Evidence-Vault"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "evidence_vault_versioning" {
  bucket = aws_s3_bucket.evidence_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence_vault_crypto" {
  bucket = aws_s3_bucket.evidence_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Forensic Evidence Registry & Hashes
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "evidence_registry" {
  name         = "finguard-evidence-registry-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "evidence_id"

  attribute {
    name = "evidence_id"
    type = "S"
  }

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "sha256_hash"
    type = "S"
  }

  global_secondary_index {
    name            = "case_id-index"
    hash_key        = "case_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "hash-lookup-index"
    hash_key        = "sha256_hash"
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
    Phase       = "Phase-22"
    Component   = "Evidence-Metadata-Registry"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Forensic Evidence Access Audit Log
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "evidence_audit" {
  name         = "finguard-evidence-audit-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audit_id"

  attribute {
    name = "audit_id"
    type = "S"
  }

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "case-audit-timeline-index"
    hash_key        = "case_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-22"
    Component   = "Evidence-Audit-Log"
    Environment = var.environment
  }
}

