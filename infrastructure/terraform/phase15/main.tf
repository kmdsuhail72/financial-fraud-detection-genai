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
}

# -----------------------------------------------------------------------------
# Neptune DB Subnet Group
# -----------------------------------------------------------------------------
resource "aws_neptune_subnet_group" "neptune_subnets" {
  name       = "finguard-neptune-subnet-group-${var.environment}"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "finguard-neptune-subnets"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-15-Graph-Analytics"
  }
}

# -----------------------------------------------------------------------------
# Security Group for Neptune Graph Cluster (Port 8182)
# -----------------------------------------------------------------------------
resource "aws_security_group" "neptune_sg" {
  name        = "finguard-neptune-sg-${var.environment}"
  description = "Controls ingress access to FinGuard Neptune graph database"
  vpc_id      = var.vpc_id

  ingress {
    description = "Gremlin and openCypher graph API access"
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "finguard-neptune-sg"
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

# -----------------------------------------------------------------------------
# Neptune Cluster Parameter Group
# -----------------------------------------------------------------------------
resource "aws_neptune_cluster_parameter_group" "neptune_params" {
  name        = "finguard-neptune-params-${var.environment}"
  family      = "neptune1.3"
  description = "FinGuard graph cluster parameter group for audit and query timeout"

  parameter {
    name  = "neptune_enable_audit_log"
    value = "1"
  }

  parameter {
    name  = "neptune_query_timeout"
    value = "30000"
  }

  tags = {
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Neptune S3 Bulk Data Loader
# -----------------------------------------------------------------------------
resource "aws_iam_role" "neptune_s3_loader_role" {
  name = "finguard-neptune-s3-loader-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "neptune_s3_loader_policy" {
  name = "neptune-s3-bulk-loader-policy"
  role = aws_iam_role.neptune_s3_loader_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Amazon Neptune Graph Cluster
# -----------------------------------------------------------------------------
resource "aws_neptune_cluster" "graph_cluster" {
  cluster_identifier                  = "finguard-fraud-graph-cluster-${var.environment}"
  engine                              = "neptune"
  engine_version                      = "1.3.1.0"
  backup_retention_period             = var.backup_retention_period
  preferred_backup_window             = "02:00-03:00"
  preferred_maintenance_window        = "sun:03:30-sun:04:30"
  skip_final_snapshot                 = true
  iam_database_authentication_enabled = var.enable_iam_database_authentication
  apply_immediately                   = true
  storage_encrypted                   = true

  neptune_subnet_group_name           = aws_neptune_subnet_group.neptune_subnets.name
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.neptune_params.name
  vpc_security_group_ids              = [aws_security_group.neptune_sg.id]

  iam_roles = [aws_iam_role.neptune_s3_loader_role.arn]

  tags = {
    Name        = "finguard-fraud-graph-cluster"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-15"
  }
}

# -----------------------------------------------------------------------------
# Amazon Neptune Cluster Primary Instance
# -----------------------------------------------------------------------------
resource "aws_neptune_cluster_instance" "graph_instance_primary" {
  identifier         = "finguard-graph-node-01"
  cluster_identifier = aws_neptune_cluster.graph_cluster.id
  instance_class     = var.neptune_instance_class
  engine             = "neptune"
  apply_immediately  = true

  tags = {
    Name        = "finguard-graph-instance-primary"
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}
