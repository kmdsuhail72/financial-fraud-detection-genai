output "identity_doc_store_bucket" {
  description = "Name of the S3 bucket for identity documents"
  value       = aws_s3_bucket.identity_doc_store.id
}

output "doc_verification_records_table" {
  description = "DynamoDB table for verification records"
  value       = aws_dynamodb_table.doc_verification_records.id
}

output "doc_audit_trail_table" {
  description = "DynamoDB table for document audit events"
  value       = aws_dynamodb_table.doc_audit_trail.id
}

