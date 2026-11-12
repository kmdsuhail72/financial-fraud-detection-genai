output "idempotency_table_name" {
  value = aws_dynamodb_table.idempotency_table.name
}

output "idempotency_table_arn" {
  value = aws_dynamodb_table.idempotency_table.arn
}

output "customer_state_table_name" {
  value = aws_dynamodb_table.customer_state_table.name
}

output "customer_state_table_arn" {
  value = aws_dynamodb_table.customer_state_table.arn
}
