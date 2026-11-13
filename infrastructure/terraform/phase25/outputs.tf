output "kyc_vault_bucket" {
  description = "Name of the S3 bucket for KYC documents"
  value       = aws_s3_bucket.kyc_vault.id
}

output "kyc_customers_table" {
  description = "DynamoDB table for KYC customer records"
  value       = aws_dynamodb_table.kyc_customers.id
}

output "screening_matches_table" {
  description = "DynamoDB table for screening matches"
  value       = aws_dynamodb_table.screening_matches.id
}

output "kyc_audit_trail_table" {
  description = "DynamoDB table for customer audit logs"
  value       = aws_dynamodb_table.kyc_audit_trail.id
}

