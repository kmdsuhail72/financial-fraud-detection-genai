output "eks_cluster_name" {
  description = "Name of the EKS Cluster"
  value       = aws_eks_cluster.finguard_eks.name
}

output "eks_cluster_endpoint" {
  description = "Endpoint URL for Kubernetes API Server"
  value       = aws_eks_cluster.finguard_eks.endpoint
}

output "eks_cluster_arn" {
  description = "ARN of the EKS Cluster"
  value       = aws_eks_cluster.finguard_eks.arn
}

output "managed_node_group_arn" {
  description = "ARN of the EKS Managed Node Group"
  value       = aws_eks_node_group.managed_nodes.arn
}
