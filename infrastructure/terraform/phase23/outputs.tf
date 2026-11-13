output "compliance_reports_bucket_arn" {
  value       = aws_s3_bucket.compliance_reports.arn
  description = "ARN of the S3 bucket for Phase 23 Compliance Reports."
}

output "governance_controls_table_arn" {
  value       = aws_dynamodb_table.governance_controls.arn
  description = "ARN of the DynamoDB table for Phase 23 Governance Controls."
}

output "governance_findings_table_arn" {
  value       = aws_dynamodb_table.governance_findings.arn
  description = "ARN of the DynamoDB table for Phase 23 Governance Findings."
}

