output "stream_name" {
  description = "Name of the provisioned Kinesis data stream"
  value       = aws_kinesis_stream.transactions_stream.name
}

output "stream_arn" {
  description = "ARN of the Kinesis data stream"
  value       = aws_kinesis_stream.transactions_stream.arn
}

output "stream_retention_period" {
  description = "Configured retention period in hours"
  value       = aws_kinesis_stream.transactions_stream.retention_period
}
