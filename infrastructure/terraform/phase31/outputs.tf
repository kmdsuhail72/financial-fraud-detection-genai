output "integration_event_archive_bucket" {
  description = "S3 bucket for banking integration raw streams and DLQ dumps"
  value       = aws_s3_bucket.integration_event_archive.id
}

output "canonical_events_table_name" {
  description = "DynamoDB table for canonical normalized events and idempotency tracking"
  value       = aws_dynamodb_table.canonical_events.name
}

output "integration_dlq_table_name" {
  description = "DynamoDB table for integration dead-letter queue records"
  value       = aws_dynamodb_table.integration_dlq.name
}
