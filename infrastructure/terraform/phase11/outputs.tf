output "cloudtrail_arn" {
  description = "ARN of the multi-region CloudTrail audit trail."
  value       = aws_cloudtrail.security_trail.arn
}

output "security_logs_bucket_arn" {
  description = "ARN of the S3 centralized security audit logs bucket."
  value       = aws_s3_bucket.security_logs.arn
}

output "security_logs_bucket_name" {
  description = "Name of the S3 centralized security audit logs bucket."
  value       = aws_s3_bucket.security_logs.id
}

output "kms_security_key_arn" {
  description = "ARN of the KMS Customer Managed Key for security logs."
  value       = aws_kms_key.security_cmk.arn
}

output "security_events_log_group" {
  description = "CloudWatch Log Group capturing CloudTrail security events."
  value       = aws_cloudwatch_log_group.security_events.name
}

output "sns_security_alerts_topic_arn" {
  description = "ARN of the SNS topic for security alarms."
  value       = aws_sns_topic.security_alerts.arn
}

