output "operations_cases_table_arn" {
  value       = aws_dynamodb_table.operations_cases.arn
  description = "ARN of the DynamoDB table for Phase 21 Operations Cases."
}

output "operations_cases_table_name" {
  value       = aws_dynamodb_table.operations_cases.name
  description = "Name of the DynamoDB table for Phase 21 Operations Cases."
}

output "alert_idempotency_table_arn" {
  value       = aws_dynamodb_table.alert_idempotency.arn
  description = "ARN of the DynamoDB table for Phase 21 Alert Idempotency."
}

output "alert_idempotency_table_name" {
  value       = aws_dynamodb_table.alert_idempotency.name
  description = "Name of the DynamoDB table for Phase 21 Alert Idempotency."
}

