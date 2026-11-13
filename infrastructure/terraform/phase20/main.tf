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
# Amazon DynamoDB Table for Idempotent Fraud Decisions (Phase 20)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "fraud_decisions" {
  name         = "finguard-fraud-decisions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "decision_id"

  attribute {
    name = "decision_id"
    type = "S"
  }

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "priority"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  # GSI 1: Lookups by Transaction ID
  global_secondary_index {
    name            = "transaction_id-index"
    hash_key        = "transaction_id"
    projection_type = "ALL"
  }

  # GSI 2: Investigation Queue Queries by Priority & Time Range
  global_secondary_index {
    name            = "priority-timestamp-index"
    hash_key        = "priority"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "finguard-fraud-decisions"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-20-Decision-Engine"
  }
}

