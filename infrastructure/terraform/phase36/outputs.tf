# Outputs for FinGuard AI Phase 36 Observability
output "cloudwatch_log_group_name" {
  description = "Name of the central CloudWatch log group for FinGuard microservices"
  value       = aws_cloudwatch_log_group.finguard_services_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the central CloudWatch log group"
  value       = aws_cloudwatch_log_group.finguard_services_logs.arn
}

output "sre_alerts_sns_topic_arn" {
  description = "ARN of the SNS topic for SRE alerts"
  value       = aws_sns_topic.sre_alerts.arn
}

output "high_5xx_alarm_arn" {
  description = "ARN of the 5xx error rate CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.high_5xx_error_rate.arn
}

output "p95_latency_alarm_arn" {
  description = "ARN of the p95 latency CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.high_p95_latency.arn
}

output "sre_dashboard_name" {
  description = "Name of the CloudWatch SRE Dashboard"
  value       = aws_cloudwatch_dashboard.finguard_sre_dashboard.dashboard_name
}
