output "neptune_cluster_id" {
  value       = aws_neptune_cluster.graph_cluster.id
  description = "Neptune cluster identifier."
}

output "neptune_cluster_endpoint" {
  value       = aws_neptune_cluster.graph_cluster.endpoint
  description = "Primary writer endpoint for Gremlin/openCypher graph queries."
}

output "neptune_reader_endpoint" {
  value       = aws_neptune_cluster.graph_cluster.reader_endpoint
  description = "Read-only replica endpoint for high-throughput analytical queries."
}

output "neptune_port" {
  value       = aws_neptune_cluster.graph_cluster.port
  description = "Port number (8182)."
}

output "neptune_security_group_id" {
  value       = aws_security_group.neptune_sg.id
  description = "Security group ID for Neptune cluster."
}

