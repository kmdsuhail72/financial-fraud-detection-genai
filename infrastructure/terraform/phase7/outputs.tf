output "dynamodb_decisions_table_name" {
  description = "Name of the DynamoDB table storing fraud scoring decisions"
  value       = aws_dynamodb_table.fraud_decisions.name
}

output "dynamodb_decisions_table_arn" {
  description = "ARN of the DynamoDB table storing fraud scoring decisions"
  value       = aws_dynamodb_table.fraud_decisions.arn
}

output "sqs_investigation_queue_url" {
  description = "URL of the SQS queue receiving high-risk investigation alerts"
  value       = aws_sqs_queue.investigation_alerts.url
}

output "sqs_investigation_queue_arn" {
  description = "ARN of the SQS queue receiving high-risk investigation alerts"
  value       = aws_sqs_queue.investigation_alerts.arn
}

output "sagemaker_model_name" {
  description = "Name of the SageMaker model resource"
  value       = aws_sagemaker_model.fraud_model.name
}

output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker real-time endpoint (if provisioned)"
  value       = var.enable_sagemaker_endpoint ? aws_sagemaker_endpoint.realtime_endpoint[0].name : "none (provisioning disabled to prevent ongoing charges)"
}

output "lambda_scoring_consumer_name" {
  description = "Name of the fraud scoring Lambda consumer function"
  value       = aws_lambda_function.scoring_consumer.function_name
}

output "lambda_scoring_consumer_arn" {
  description = "ARN of the fraud scoring Lambda consumer function"
  value       = aws_lambda_function.scoring_consumer.arn
}

