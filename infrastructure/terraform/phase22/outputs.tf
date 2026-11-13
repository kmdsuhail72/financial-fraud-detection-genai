output "evidence_vault_bucket_arn" {
  value       = aws_s3_bucket.evidence_vault.arn
  description = "ARN of the S3 bucket for Phase 22 Digital Evidence Vault."
}

output "evidence_vault_bucket_name" {
  value       = aws_s3_bucket.evidence_vault.bucket
  description = "Name of the S3 bucket for Phase 22 Digital Evidence Vault."
}

output "evidence_registry_table_arn" {
  value       = aws_dynamodb_table.evidence_registry.arn
  description = "ARN of the DynamoDB table for Phase 22 Evidence Registry."
}

output "evidence_audit_table_arn" {
  value       = aws_dynamodb_table.evidence_audit.arn
  description = "ARN of the DynamoDB table for Phase 22 Evidence Audit."
}

