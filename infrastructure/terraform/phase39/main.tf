# ==============================================================================
# FinGuard AI — Phase 39: Amazon ElastiCache for Redis Terraform Foundation
# Multi-AZ Replication Group with In-Transit & At-Rest Encryption (ap-south-1)
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "FinGuard-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase-39-Caching"
    }
  }
}

# --- Cache Subnet Group ---
resource "aws_elasticache_subnet_group" "redis_subnets" {
  name        = "${var.environment}-finguard-redis-subnet-group"
  description = "Subnet group for FinGuard Redis replication group across AZs"
  subnet_ids  = var.cache_subnet_ids
}

# --- Security Group for Redis Cluster ---
resource "aws_security_group" "redis_sg" {
  name        = "${var.environment}-finguard-redis-sg"
  description = "Security group for FinGuard Redis ElastiCache cluster"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow inbound Redis traffic from application microservices"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.app_vpc_cidr]
  }

  egress {
    description = "Outbound traffic rule"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-redis-sg"
  }
}

# --- Custom Parameter Group ---
resource "aws_elasticache_parameter_group" "redis_params" {
  name        = "${var.environment}-finguard-redis7-params"
  family      = "redis7"
  description = "FinGuard Redis 7.x parameter group with volatile-lru eviction"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"
  }
}

# --- Redis Multi-AZ Replication Group ---
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.environment}-finguard-redis"
  description                   = "FinGuard AI Enterprise Redis Cache and Rate Limiting Cluster"
  node_type                     = var.node_type
  num_cache_clusters            = var.num_cache_clusters
  port                          = 6379
  parameter_group_name          = aws_elasticache_parameter_group.redis_params.name
  subnet_group_name             = aws_elasticache_subnet_group.redis_subnets.name
  security_group_ids            = [aws_security_group.redis_sg.id]
  automatic_failover_enabled    = true
  multi_az_enabled              = true
  engine                        = "redis"
  engine_version                = "7.1"
  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = true
  auth_token                    = var.auth_token != "" ? var.auth_token : null

  snapshot_retention_limit = 7
  snapshot_window          = "00:00-01:00"
  maintenance_window       = "sun:05:00-sun:06:00"

  auto_minor_version_upgrade = true
  apply_immediately         = false

  tags = {
    Name = "${var.environment}-finguard-redis-replication-group"
  }
}
