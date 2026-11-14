# ==============================================================================
# FinGuard AI — Phase 39: Terraform Outputs
# ==============================================================================

output "primary_endpoint_address" {
  description = "Primary write endpoint address for Redis replication group"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "Read-only replica endpoint address for load-balanced queries"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
}

output "redis_port" {
  description = "Port exposed by Redis nodes"
  value       = aws_elasticache_replication_group.redis.port
}

output "replication_group_id" {
  description = "ElastiCache replication group identifier"
  value       = aws_elasticache_replication_group.redis.id
}
