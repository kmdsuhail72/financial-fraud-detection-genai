# ==============================================================================
# FinGuard AI — Phase 40: Terraform Outputs
# ==============================================================================

output "sns_topic_arn" {
  description = "ARN of the SNS Fan-Out Topic"
  value       = aws_sns_topic.transactions_fanout.arn
}

output "fraud_queue_url" {
  description = "URL of SQS Fraud Scoring Queue"
  value       = aws_sqs_queue.fraud_queue.id
}

output "notifications_queue_url" {
  description = "URL of SQS Notifications Queue"
  value       = aws_sqs_queue.notifications_queue.id
}

output "audit_fifo_queue_url" {
  description = "URL of SQS FIFO Audit Queue"
  value       = aws_sqs_queue.audit_fifo_queue.id
}

output "dlq_url" {
  description = "URL of Dead-Letter Queue"
  value       = aws_sqs_queue.finguard_dlq.id
}

output "eventbridge_bus_arn" {
  description = "ARN of EventBridge Custom Event Bus"
  value       = aws_cloudwatch_event_bus.finguard_bus.arn
}
