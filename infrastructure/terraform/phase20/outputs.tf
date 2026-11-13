output "dynamodb_table_name" {
  description = "Name of the DynamoDB fraud decision table."
  value       = aws_dynamodb_table.fraud_decisions.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB fraud decision table."
  value       = aws_dynamodb_table.fraud_decisions.arn
}

