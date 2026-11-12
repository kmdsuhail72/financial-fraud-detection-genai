output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool."
  value       = aws_cognito_user_pool.fraud_analysts.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool."
  value       = aws_cognito_user_pool.fraud_analysts.arn
}

output "cognito_app_client_id" {
  description = "Public Client ID for React SPA authentication."
  value       = aws_cognito_user_pool_client.analyst_portal_client.id
}

output "cognito_issuer_url" {
  description = "OIDC Issuer URL for JWT verification."
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.fraud_analysts.id}"
}

output "audit_table_name" {
  description = "DynamoDB table name for security audit logs."
  value       = aws_dynamodb_table.security_audit.name
}

output "audit_table_arn" {
  description = "ARN of the security audit DynamoDB table."
  value       = aws_dynamodb_table.security_audit.arn
}

