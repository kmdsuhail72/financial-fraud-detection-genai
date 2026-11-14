# Terraform Module for FinGuard AI Phase 37 — Multi-Region HA, S3 CRR & DynamoDB PITR
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Primary Region Provider: AWS Mumbai (ap-south-1)
provider "aws" {
  alias  = "primary"
  region = var.primary_region
}

# Secondary Region Provider: AWS Singapore (ap-southeast-1)
provider "aws" {
  alias  = "secondary"
  region = var.secondary_region
}

# ==============================================================================
# S3 Cross-Region Replication (CRR)
# ==============================================================================

# 1. Replica Bucket in Secondary Region (Singapore)
resource "aws_s3_bucket" "replica_bucket" {
  provider = aws.secondary
  bucket   = "${var.bucket_prefix}-replica-${var.secondary_region}"

  tags = {
    Environment = var.environment
    Role        = "DR-Replica"
    Project     = "FinGuard-AI"
  }
}

resource "aws_s3_bucket_versioning" "replica_versioning" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.replica_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "replica_crypto" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.replica_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 2. Primary Bucket in Primary Region (Mumbai)
resource "aws_s3_bucket" "primary_bucket" {
  provider = aws.primary
  bucket   = "${var.bucket_prefix}-primary-${var.primary_region}"

  tags = {
    Environment = var.environment
    Role        = "Primary-Source"
    Project     = "FinGuard-AI"
  }
}

resource "aws_s3_bucket_versioning" "primary_versioning" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 3. IAM Role for S3 Replication
resource "aws_iam_role" "replication_role" {
  provider = aws.primary
  name     = "finguard-s3-replication-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "replication_policy" {
  provider = aws.primary
  name     = "finguard-s3-replication-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [aws_s3_bucket.primary_bucket.arn]
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Effect   = "Allow"
        Resource = ["${aws_s3_bucket.primary_bucket.arn}/*"]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect   = "Allow"
        Resource = ["${aws_s3_bucket.replica_bucket.arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "replication_attach" {
  provider   = aws.primary
  role       = aws_iam_role.replication_role.name
  policy_arn = aws_iam_policy.replication_policy.arn
}

# 4. S3 Replication Configuration Rule
resource "aws_s3_bucket_replication_configuration" "crr" {
  provider = aws.primary
  depends_on = [
    aws_s3_bucket_versioning.primary_versioning,
    aws_s3_bucket_versioning.replica_versioning,
  ]

  role   = aws_iam_role.replication_role.arn
  bucket = aws_s3_bucket.primary_bucket.id

  rule {
    id     = "CRR-To-Singapore"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.replica_bucket.arn
      storage_class = "STANDARD"
    }
  }
}

# ==============================================================================
# DynamoDB Recovery State Table with Point-In-Time Recovery (PITR)
# ==============================================================================
resource "aws_dynamodb_table" "dr_recovery_state" {
  provider     = aws.primary
  name         = "finguard-dr-recovery-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "service_id"
  range_key    = "snapshot_timestamp"

  attribute {
    name = "service_id"
    type = "S"
  }

  attribute {
    name = "snapshot_timestamp"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Module      = "DisasterRecovery"
    PITR        = "Enabled"
  }
}

# ==============================================================================
# Route 53 Primary Health Check & DNS Failover Policy Foundation
# ==============================================================================
resource "aws_route53_health_check" "primary_mumbai_health" {
  provider          = aws.primary
  fqdn              = "api.mumbai.finguard.internal"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 10

  tags = {
    Name        = "FinGuard-Primary-Mumbai-HealthCheck"
    Environment = var.environment
  }
}
