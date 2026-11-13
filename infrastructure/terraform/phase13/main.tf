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
# Customer Managed KMS Key for Threat Intelligence Archive
# -----------------------------------------------------------------------------
resource "aws_kms_key" "threat_intel_kms" {
  description             = "FinGuard AI Threat Intelligence Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "finguard-threat-intel-kms"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-13"
  }
}

resource "aws_kms_alias" "threat_intel_kms_alias" {
  name          = "alias/finguard-threat-intel-key-${var.environment}"
  target_key_id = aws_kms_key.threat_intel_kms.key_id
}

# -----------------------------------------------------------------------------
# Encrypted S3 Bucket for Threat Intelligence Telemetry & IOC Archives
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "threat_intel_bucket" {
  bucket        = "finguard-threat-intel-archive-${var.environment}"
  force_destroy = false

  tags = {
    Name        = "finguard-threat-intel-archive"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-13"
  }
}

resource "aws_s3_bucket_versioning" "threat_intel_versioning" {
  bucket = aws_s3_bucket.threat_intel_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "threat_intel_encryption" {
  bucket = aws_s3_bucket.threat_intel_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.threat_intel_kms.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "threat_intel_public_block" {
  bucket = aws_s3_bucket.threat_intel_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "threat_intel_lifecycle" {
  bucket = aws_s3_bucket.threat_intel_bucket.id

  rule {
    id     = "archive-transition"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.retention_days
    }
  }
}

