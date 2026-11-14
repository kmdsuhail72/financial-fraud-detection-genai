variable "aws_region" {
  description = "AWS region for EKS deployment"
  type        = string
  default     = "ap-south-1" # Mumbai
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "EKS Cluster Name"
  type        = string
  default     = "finguard-eks-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes Version for EKS Control Plane"
  type        = string
  default     = "1.29"
}

variable "vpc_cidr" {
  description = "VPC CIDR for EKS Cluster"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "EC2 Instance Types for EKS Managed Node Group"
  type        = list(string)
  default     = ["m5.large", "t3.medium"]
}
