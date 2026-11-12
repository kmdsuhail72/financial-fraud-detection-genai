output "dynamodb_cases_table_name" {
  description = "Name of the DynamoDB table storing fraud investigation cases"
  value       = aws_dynamodb_table.investigation_cases.name
}

output "dynamodb_cases_table_arn" {
  description = "ARN of the DynamoDB table storing fraud investigation cases"
  value       = aws_dynamodb_table.investigation_cases.arn
}

output "lambda_case_orchestrator_name" {
  description = "Name of the case orchestrator Lambda function"
  value       = aws_lambda_function.case_orchestrator.function_name
}

output "lambda_case_orchestrator_arn" {
  description = "ARN of the case orchestrator Lambda function"
  value       = aws_lambda_function.case_orchestrator.arn
}
