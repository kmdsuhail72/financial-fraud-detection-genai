# Idempotency Table with TTL
resource "aws_dynamodb_table" "idempotency_table" {
  name         = "${var.project_name}-idempotency-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  tags = {
    Name        = "${var.project_name}-idempotency-${var.environment}"
    Environment = var.environment
  }
}

# Customer Feature State Table
resource "aws_dynamodb_table" "customer_state_table" {
  name         = "${var.project_name}-customer-state-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  tags = {
    Name        = "${var.project_name}-customer-state-${var.environment}"
    Environment = var.environment
  }
}

