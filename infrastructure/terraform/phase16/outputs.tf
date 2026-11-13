output "kinesis_graph_stream_name" {
  value       = aws_kinesis_stream.graph_stream.name
  description = "Name of the Kinesis Data Stream ingesting graph transaction events"
}

output "kinesis_graph_stream_arn" {
  value       = aws_kinesis_stream.graph_stream.arn
  description = "ARN of the Kinesis Data Stream"
}

output "neptune_cluster_endpoint" {
  value       = aws_neptune_cluster.neptune.endpoint
  description = "Writer endpoint for Amazon Neptune Gremlin / SPARQL graph queries"
}

output "neptune_cluster_port" {
  value       = aws_neptune_cluster.neptune.port
  description = "Port number for Neptune cluster connectivity (8182)"
}

output "lambda_graph_processor_arn" {
  value       = aws_lambda_function.graph_processor.arn
  description = "ARN of the Kinesis-to-Neptune Lambda event processor"
}

output "cleanup_instructions" {
  value       = "To tear down Neptune resources and avoid ongoing AWS billing: run 'terraform destroy -auto-approve' in infrastructure/terraform/phase16"
  description = "Cost management and resource decommissioning guide"
}
