output "payment_event_lake_bucket_name" {
  description = "Name of the S3 bucket hosting raw payment gateway streams"
  value       = aws_s3_bucket.payment_event_lake.id
}

output "payment_assessments_table_name" {
  description = "DynamoDB table name for real-time payment risk assessments"
  value       = aws_dynamodb_table.payment_assessments.name
}

output "payment_velocity_table_name" {
  description = "DynamoDB table name for rolling payment velocity tracking"
  value       = aws_dynamodb_table.payment_velocity_window.name
}

