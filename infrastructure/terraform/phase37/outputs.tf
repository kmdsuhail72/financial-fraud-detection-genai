# Outputs for FinGuard AI Phase 37 Disaster Recovery
output "primary_bucket_arn" {
  description = "ARN of the primary Mumbai S3 evidence bucket"
  value       = aws_s3_bucket.primary_bucket.arn
}

output "replica_bucket_arn" {
  description = "ARN of the secondary Singapore replica S3 bucket"
  value       = aws_s3_bucket.replica_bucket.arn
}

output "s3_replication_role_arn" {
  description = "ARN of the IAM role executing S3 Cross-Region Replication"
  value       = aws_iam_role.replication_role.arn
}

output "dynamodb_dr_table_arn" {
  description = "ARN of the DynamoDB recovery state table with PITR enabled"
  value       = aws_dynamodb_table.dr_recovery_state.arn
}

output "route53_primary_health_check_id" {
  description = "ID of the Route 53 health check monitoring Mumbai API endpoints"
  value       = aws_route53_health_check.primary_mumbai_health.id
}

