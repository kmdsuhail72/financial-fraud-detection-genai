output "eventbridge_bus_arn" {
  description = "ARN of the FinGuard EventBridge Custom Event Bus"
  value       = aws_cloudwatch_event_bus.finguard_event_bus.arn
}

output "eventbridge_bus_name" {
  description = "Name of the FinGuard EventBridge Event Bus"
  value       = aws_cloudwatch_event_bus.finguard_event_bus.name
}

output "transaction_queue_url" {
  description = "URL of the SQS Transaction Processing Queue"
  value       = aws_sqs_queue.transaction_processing_queue.id
}

output "transaction_dlq_url" {
  description = "URL of the SQS Dead-Letter Queue"
  value       = aws_sqs_queue.transaction_dlq.id
}

output "fraud_alerts_topic_arn" {
  description = "ARN of the SNS Fraud Alerts Topic"
  value       = aws_sns_topic.fraud_alerts_topic.arn
}

