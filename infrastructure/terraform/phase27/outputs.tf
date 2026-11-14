output "identity_graph_vault_bucket" {
  description = "Name of the S3 bucket for identity graph snapshots"
  value       = aws_s3_bucket.identity_graph_vault.id
}

output "identity_nodes_table" {
  description = "DynamoDB table for identity graph nodes"
  value       = aws_dynamodb_table.identity_nodes.id
}

output "identity_collisions_table" {
  description = "DynamoDB table for identity collisions"
  value       = aws_dynamodb_table.identity_collisions.id
}

output "identity_audit_trail_table" {
  description = "DynamoDB table for identity audit trail"
  value       = aws_dynamodb_table.identity_audit_trail.id
}

