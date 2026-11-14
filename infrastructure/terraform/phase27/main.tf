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
# Amazon S3 Bucket for Identity Graph Snapshots & Network Backups (Phase 27)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "identity_graph_vault" {
  bucket        = "finguard-identity-graph-vault-${var.environment}"
  force_destroy = false

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-27"
    Component   = "Identity-Graph-Vault"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "identity_graph_vault_versioning" {
  bucket = aws_s3_bucket.identity_graph_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "identity_graph_vault_crypto" {
  bucket = aws_s3_bucket.identity_graph_vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Identity Graph Nodes & Adjacency
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "identity_nodes" {
  name         = "finguard-identity-nodes-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "node_id"

  attribute {
    name = "node_id"
    type = "S"
  }

  attribute {
    name = "node_type"
    type = "S"
  }

  global_secondary_index {
    name            = "NodeTypeIndex"
    hash_key        = "node_type"
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
    Phase       = "Phase-27"
    Component   = "Identity-Graph-Nodes"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Identity Collisions & Ring Clusters
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "identity_collisions" {
  name         = "finguard-identity-collisions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "collision_id"

  attribute {
    name = "collision_id"
    type = "S"
  }

  attribute {
    name = "severity"
    type = "S"
  }

  global_secondary_index {
    name            = "SeverityIndex"
    hash_key        = "severity"
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
    Phase       = "Phase-27"
    Component   = "Identity-Collisions"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Identity Audit Trail
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "identity_audit_trail" {
  name         = "finguard-identity-audit-trail-${var.environment}"
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
    Phase       = "Phase-27"
    Component   = "Identity-Audit-Trail"
    Environment = var.environment
  }
}

