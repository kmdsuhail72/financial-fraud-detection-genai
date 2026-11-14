# Phase 33 — AWS EventBridge, SQS, DLQ and SNS Microservices Event Foundation

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 1. AWS EventBridge Custom Event Bus
resource "aws_cloudwatch_event_bus" "finguard_event_bus" {
  name = "${var.environment}-finguard-event-bus"

  tags = {
    Environment = var.environment
    Service     = "finguard-event-architecture"
    Phase       = "33"
  }
}

# 2. Dead-Letter Queue (DLQ) for Failed / Poison Events
resource "aws_sqs_queue" "transaction_dlq" {
  name                      = "${var.environment}-finguard-transaction-dlq"
  message_retention_seconds = 1209600 # 14 days retention for investigation

  tags = {
    Environment = var.environment
    Service     = "finguard-dead-letter-queue"
    Phase       = "33"
  }
}

# 3. Main Transaction SQS Queue with Redrive Policy pointing to DLQ
resource "aws_sqs_queue" "transaction_processing_queue" {
  name                       = "${var.environment}-finguard-transaction-queue"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.transaction_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Environment = var.environment
    Service     = "finguard-transaction-processor"
    Phase       = "33"
  }
}

# 4. SNS Topic for Critical Fraud Alerts & Saga Compensation Broadcasts
resource "aws_sns_topic" "fraud_alerts_topic" {
  name = "${var.environment}-finguard-fraud-alerts-topic"

  tags = {
    Environment = var.environment
    Service     = "finguard-notifications"
    Phase       = "33"
  }
}

# 5. EventBridge Rule routing Transaction Initiated events to SQS
resource "aws_cloudwatch_event_rule" "transaction_initiated_rule" {
  name           = "${var.environment}-finguard-txn-initiated-rule"
  description    = "Routes transaction.initiated.v1 events to transaction processing queue"
  event_bus_name = aws_cloudwatch_event_bus.finguard_event_bus.name

  event_pattern = jsonencode({
    source      = ["transaction-service"]
    detail-type = ["transaction.initiated.v1"]
  })

  tags = {
    Environment = var.environment
    Phase       = "33"
  }
}

resource "aws_cloudwatch_event_target" "sqs_target" {
  rule           = aws_cloudwatch_event_rule.transaction_initiated_rule.name
  event_bus_name = aws_cloudwatch_event_bus.finguard_event_bus.name
  target_id      = "SendToTransactionQueue"
  arn            = aws_sqs_queue.transaction_processing_queue.arn

  dead_letter_config {
    arn = aws_sqs_queue.transaction_dlq.arn
  }
}
