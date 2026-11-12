# Kinesis Dev Environment Configuration
output "kinesis_stream_name" {
  description = "Dev Kinesis Stream Name"
  value       = module.kinesis.stream_name
}

output "kinesis_stream_arn" {
  description = "Dev Kinesis Stream ARN"
  value       = module.kinesis.stream_arn
}

