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
# Amazon DynamoDB Table for Operations Cases & SLA Management (Phase 21)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "operations_cases" {
  name         = "finguard-operations-cases-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "case_id"

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "priority"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "assigned_to"
    type = "S"
  }

  attribute {
    name = "sla_deadline"
    type = "S"
  }

  # GSI 1: Tenant Queue Sorted by SLA Deadline (Ascending urgency)
  global_secondary_index {
    name            = "tenant-sla-index"
    hash_key        = "tenant_id"
    range_key       = "sla_deadline"
    projection_type = "ALL"
  }

  # GSI 2: Tenant Cases Filtered by Operational Status
  global_secondary_index {
    name            = "tenant-status-index"
    hash_key        = "tenant_id"
    range_key       = "status"
    projection_type = "ALL"
  }

  # GSI 3: Analyst Workload and Assigned Active Cases
  global_secondary_index {
    name            = "analyst-workload-index"
    hash_key        = "assigned_to"
    range_key       = "sla_deadline"
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
    Phase       = "Phase-21"
    Component   = "Operations-Queue-SLA-Store"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Amazon DynamoDB Table for Tenant-Scoped Alert Idempotency
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "alert_idempotency" {
  name         = "finguard-alert-idempotency-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"
  range_key    = "idempotency_key"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "FinGuard-AI"
    Phase       = "Phase-21"
    Component   = "Tenant-Alert-Idempotency"
    Environment = var.environment
  }
}

