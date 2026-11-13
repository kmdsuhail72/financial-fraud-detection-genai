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
# Amazon Kinesis Data Stream for Real-Time Graph Telemetry
# -----------------------------------------------------------------------------
resource "aws_kinesis_stream" "graph_stream" {
  name             = "finguard-graph-stream-${var.environment}"
  shard_count      = var.kinesis_shard_count
  retention_period = 24

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
    "IteratorAgeMilliseconds",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name        = "finguard-graph-stream"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-16-Neptune-Streaming"
  }
}

# -----------------------------------------------------------------------------
# Neptune DB Subnet Group & Security Group
# -----------------------------------------------------------------------------
resource "aws_neptune_subnet_group" "neptune_subnets" {
  name       = "finguard-neptune-subnet-group-${var.environment}"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "finguard-neptune-subnets"
    Environment = var.environment
    Project     = "FinGuard AI"
    Phase       = "Phase-16-Neptune-Streaming"
  }
}

resource "aws_security_group" "neptune_sg" {
  name        = "finguard-neptune-sg-${var.environment}"
  description = "Controls ingress access to FinGuard Neptune graph database"
  vpc_id      = var.vpc_id

  ingress {
    description = "Gremlin traversal API access (Port 8182)"
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow outbound connectivity"
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
# Amazon Neptune Cluster (Small Dev Configuration)
# Note: Neptune is a provisioned cluster; keep instances minimal for dev/demo.
# -----------------------------------------------------------------------------
resource "aws_neptune_cluster" "neptune" {
  cluster_identifier                  = "finguard-neptune-${var.environment}"
  engine                              = "neptune"
  engine_version                      = var.neptune_engine_version
  backup_retention_period             = 1
  preferred_backup_window             = "02:00-03:00"
  preferred_maintenance_window        = "sun:03:30-sun:04:30"
  neptune_subnet_group_name           = aws_neptune_subnet_group.neptune_subnets.name
  vpc_security_group_ids              = [aws_security_group.neptune_sg.id]
  iam_database_authentication_enabled = false
  skip_final_snapshot                 = true
  deletion_protection                 = false

  tags = {
    Name        = "finguard-neptune-cluster"
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

resource "aws_neptune_cluster_instance" "neptune_instances" {
  count              = var.neptune_instance_count
  cluster_identifier = aws_neptune_cluster.neptune.id
  identifier         = "finguard-neptune-node-${count.index}-${var.environment}"
  instance_class     = var.neptune_instance_class
  engine             = "neptune"

  tags = {
    Name        = "finguard-neptune-node-${count.index}"
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Kinesis-to-Neptune Graph Event Processor Lambda
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_graph_role" {
  name = "finguard-lambda-graph-sync-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

resource "aws_iam_policy" "lambda_graph_policy" {
  name        = "finguard-lambda-graph-sync-policy-${var.environment}"
  description = "Allows Lambda to read Kinesis stream, connect to Neptune, and write CloudWatch logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ]
        Resource = aws_kinesis_stream.graph_stream.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_graph_attach" {
  role       = aws_iam_role.lambda_graph_role.name
  policy_arn = aws_iam_policy.lambda_graph_policy.arn
}

# -----------------------------------------------------------------------------
# AWS Lambda Function: Real-Time Graph Processor
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "graph_processor" {
  function_name = "finguard-graph-event-processor-${var.environment}"
  role          = aws_iam_role.lambda_graph_role.arn
  handler       = "lambda_graph_sync.handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      NEPTUNE_ENDPOINT   = aws_neptune_cluster.neptune.endpoint
      NEPTUNE_PORT       = "8182"
      NEPTUNE_LOCAL_MODE = "false"
      ENVIRONMENT        = var.environment
    }
  }

  tags = {
    Name        = "finguard-graph-processor"
    Environment = var.environment
    Project     = "FinGuard AI"
  }
}

# Event Source Mapping: Kinesis -> Lambda
resource "aws_lambda_event_source_mapping" "kinesis_to_lambda" {
  event_source_arn                   = aws_kinesis_stream.graph_stream.arn
  function_name                      = aws_lambda_function.graph_processor.arn
  starting_position                  = "LATEST"
  batch_size                         = 100
  maximum_batching_window_in_seconds = 2
  bisect_batch_on_function_error     = true
  function_response_types            = ["ReportBatchItemFailures"]
}

# -----------------------------------------------------------------------------
# CloudWatch Operational Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "finguard-graph-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Triggered when graph synchronization Lambda fails repeatedly."

  dimensions = {
    FunctionName = aws_lambda_function.graph_processor.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "finguard-graph-kinesis-iterator-lag-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 300
  statistic           = "Maximum"
  threshold           = 60000
  alarm_description   = "Triggered when stream ingestion backlog exceeds 60 seconds."

  dimensions = {
    StreamName = aws_kinesis_stream.graph_stream.name
  }
}

