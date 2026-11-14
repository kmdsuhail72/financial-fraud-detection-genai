output "risk_dossier_vault_bucket" {
  description = "Name of the S3 bucket for customer risk dossiers"
  value       = aws_s3_bucket.risk_dossier_vault.id
}

output "customer_risk_assessments_table" {
  description = "DynamoDB table for customer risk assessments"
  value       = aws_dynamodb_table.customer_risk_assessments.id
}

output "customer_risk_history_table" {
  description = "DynamoDB table for customer continuous risk history"
  value       = aws_dynamodb_table.customer_risk_history.id
}

