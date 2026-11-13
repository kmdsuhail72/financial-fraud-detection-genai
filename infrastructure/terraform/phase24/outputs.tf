output "sar_vault_bucket_arn" {
  value       = aws_s3_bucket.sar_vault.arn
  description = "ARN of the S3 bucket for Phase 24 SAR Drafts."
}

output "aml_cases_table_arn" {
  value       = aws_dynamodb_table.aml_cases.arn
  description = "ARN of the DynamoDB table for Phase 24 AML Cases."
}

output "customer_risk_profiles_table_arn" {
  value       = aws_dynamodb_table.customer_risk_profiles.arn
  description = "ARN of the DynamoDB table for Phase 24 Customer Risk Profiles."
}

