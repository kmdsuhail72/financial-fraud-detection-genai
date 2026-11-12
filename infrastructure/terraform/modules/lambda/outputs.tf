output "lambda_function_name" {
  value = aws_lambda_function.transaction_processor.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.transaction_processor.arn
}

output "event_source_mapping_uuid" {
  value = aws_lambda_event_source_mapping.kinesis_esm.uuid
}
