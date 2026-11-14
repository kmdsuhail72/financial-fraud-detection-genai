output "regulatory_filing_vault_bucket_name" {
  description = "Name of S3 bucket storing regulatory filing dossiers"
  value       = aws_s3_bucket.regulatory_filing_vault.id
}

output "regulatory_reports_table_name" {
  description = "DynamoDB table name for regulatory SAR/STR reports"
  value       = aws_dynamodb_table.regulatory_reports.name
}

output "regulatory_audit_events_table_name" {
  description = "DynamoDB table name for immutable regulatory audit trail"
  value       = aws_dynamodb_table.regulatory_audit_events.name
}

