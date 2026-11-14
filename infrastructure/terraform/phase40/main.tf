# ==============================================================================
# FinGuard AI — Phase 40: Amazon SQS, SNS & EventBridge Terraform Foundation
# Fan-Out, Dead-Letter Queues (DLQ), FIFO Deduplication & Content Routing
# ==============================================================================

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
  default_tags {
    tags = {
      Project     = "FinGuard-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase-40-Messaging"
    }
  }
}

# --- 1. Dead-Letter Queue (DLQ) ---
resource "aws_sqs_queue" "finguard_dlq" {
  name                      = "${var.environment}-finguard-main-dlq"
  message_retention_seconds = 1209600 # 14 days quarantine retention
  kms_master_key_id         = "alias/aws/sqs"
}

# --- 2. SQS Standard Queue: Fraud Scoring ---
resource "aws_sqs_queue" "fraud_queue" {
  name                       = "${var.environment}-finguard-fraud-scoring"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 345600 # 4 days
  kms_master_key_id          = "alias/aws/sqs"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.finguard_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

# --- 3. SQS Standard Queue: Notifications ---
resource "aws_sqs_queue" "notifications_queue" {
  name                       = "${var.environment}-finguard-notifications"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 345600 # 4 days
  kms_master_key_id          = "alias/aws/sqs"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.finguard_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

# --- 4. SQS FIFO Queue: Immutable Audit Ledger ---
resource "aws_sqs_queue" "audit_fifo_queue" {
  name                        = "${var.environment}-finguard-audit-ledger.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  deduplication_scope         = "messageGroup"
  fifo_throughput_limit       = "perMessageGroupId"
  kms_master_key_id           = "alias/aws/sqs"
}

# --- 5. Amazon SNS Topic for Fan-Out ---
resource "aws_sns_topic" "transactions_fanout" {
  name              = "${var.environment}-finguard-transactions-fanout"
  kms_master_key_id = "alias/aws/sns"
}

# --- 6. SNS Subscriptions (Fan-out to SQS Queues) ---
resource "aws_sns_topic_subscription" "fraud_queue_sub" {
  topic_arn            = aws_sns_topic.transactions_fanout.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.fraud_queue.arn
  raw_message_delivery = true
}

resource "aws_sns_topic_subscription" "notifications_queue_sub" {
  topic_arn            = aws_sns_topic.transactions_fanout.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.notifications_queue.arn
  raw_message_delivery = true
}

# --- 7. Amazon EventBridge Custom Bus & Content Rule ---
resource "aws_cloudwatch_event_bus" "finguard_bus" {
  name = "${var.environment}-finguard-enterprise-bus"
}

resource "aws_cloudwatch_event_rule" "high_value_rule" {
  name           = "${var.environment}-high-value-transactions"
  description    = "Routes transactions with amount >= 100,000 to compliance queue"
  event_bus_name = aws_cloudwatch_event_bus.finguard_bus.name

  event_pattern = jsonencode({
    source = ["finguard.transactions"]
    detail = {
      amount = [{ numeric = [">=", 100000] }]
    }
  })
}

resource "aws_cloudwatch_event_target" "high_value_target" {
  rule           = aws_cloudwatch_event_rule.high_value_rule.name
  event_bus_name = aws_cloudwatch_event_bus.finguard_bus.name
  arn            = aws_sqs_queue.fraud_queue.arn
}
