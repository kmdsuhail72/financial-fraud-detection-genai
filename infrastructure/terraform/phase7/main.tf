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
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase7"
    }
  }
}

# -----------------------------------------------------------------------------
# 1. DynamoDB: Transaction Decisions & Idempotency Store
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "fraud_decisions" {
  name         = "${var.project_name}-fraud-decisions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "risk_level"
    type = "S"
  }

  attribute {
    name = "decision_timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "RiskLevelIndex"
    hash_key        = "risk_level"
    range_key       = "decision_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-fraud-decisions-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# 2. Amazon SQS: Investigation Alerts Queue & Dead-Letter Queue
# -----------------------------------------------------------------------------
resource "aws_sqs_queue" "investigation_alerts_dlq" {
  name                      = "${var.project_name}-investigation-alerts-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "investigation_alerts" {
  name                      = "${var.project_name}-investigation-alerts-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  visibility_timeout_seconds = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.investigation_alerts_dlq.arn
    maxReceiveCount     = 3
  })
}

# -----------------------------------------------------------------------------
# 3. Amazon SageMaker: Model, Endpoint Config & Real-Time Endpoint
# -----------------------------------------------------------------------------
resource "aws_iam_role" "sagemaker_role" {
  name = "${var.project_name}-sagemaker-endpoint-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "sagemaker_policy" {
  name = "${var.project_name}-sagemaker-endpoint-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.artifact_bucket_name}",
          "arn:aws:s3:::${var.artifact_bucket_name}/*"
        ]
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
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_attach" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = aws_iam_policy.sagemaker_policy.arn
}

resource "aws_sagemaker_model" "fraud_model" {
  name               = "${var.project_name}-fraud-model-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    image          = var.sagemaker_image_uri
    model_data_url = var.model_data_url
    environment = {
      SAGEMAKER_PROGRAM           = "code/inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY  = var.model_data_url
      MODEL_FEATURE_COLUMNS_JSON = var.model_feature_columns_json
    }
  }
}

resource "aws_sagemaker_endpoint_configuration" "endpoint_config" {
  count = var.enable_sagemaker_endpoint ? 1 : 0
  name  = "${var.project_name}-endpoint-config-${var.environment}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.fraud_model.name
    initial_instance_count = 1
    instance_type          = var.sagemaker_instance_type
  }
}

resource "aws_sagemaker_endpoint" "realtime_endpoint" {
  count                = var.enable_sagemaker_endpoint ? 1 : 0
  name                 = "${var.project_name}-fraud-endpoint-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.endpoint_config[0].name
}

# -----------------------------------------------------------------------------
# 4. AWS Lambda: Real-Time Fraud Scoring Consumer
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_scoring_role" {
  name = "${var.project_name}-lambda-scoring-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_scoring_policy" {
  name = "${var.project_name}-lambda-scoring-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KinesisRead"
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ]
        Resource = var.kinesis_stream_arn
      },
      {
        Sid    = "DynamoDBWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.fraud_decisions.arn,
          "${aws_dynamodb_table.fraud_decisions.arn}/index/*"
        ]
      },
      {
        Sid    = "SQSAlerts"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.investigation_alerts.arn
      },
      {
        Sid    = "SageMakerInvoke"
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = "arn:aws:sagemaker:${var.aws_region}:*:endpoint/*"
      },
      {
        Sid    = "CloudWatchLogsAndMetrics"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_scoring_attach" {
  role       = aws_iam_role.lambda_scoring_role.name
  policy_arn = aws_iam_policy.lambda_scoring_policy.arn
}

# Stub Lambda deployment package (replaced during CI/CD package deployment)
data "archive_file" "lambda_scoring_dummy" {
  type        = "zip"
  output_path = "${path.module}/lambda_scoring_dummy.zip"

  source {
    content  = "def lambda_handler(event, context): return {'batchItemFailures': []}"
    filename = "handler.py"
  }
}

resource "aws_lambda_function" "scoring_consumer" {
  function_name    = "${var.project_name}-fraud-scoring-consumer-${var.environment}"
  role             = aws_iam_role.lambda_scoring_role.arn
  handler          = "lambda_scoring.handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 512
  filename         = data.archive_file.lambda_scoring_dummy.output_path
  source_code_hash = data.archive_file.lambda_scoring_dummy.output_base64sha256

  environment {
    variables = {
      SAGEMAKER_ENDPOINT_NAME     = var.enable_sagemaker_endpoint ? aws_sagemaker_endpoint.realtime_endpoint[0].name : "mock"
      DYNAMODB_TABLE_DECISIONS   = aws_dynamodb_table.fraud_decisions.name
      SQS_INVESTIGATION_QUEUE_URL = aws_sqs_queue.investigation_alerts.url
      AWS_REGION                  = var.aws_region
      RISK_THRESHOLD_HIGH         = "0.60"
      RISK_THRESHOLD_REVIEW       = "0.35"
      WEIGHT_FRAUD_PROBABILITY    = "0.65"
      WEIGHT_ANOMALY_SCORE        = "0.35"
      DECISION_TTL_DAYS           = "90"
    }
  }
}

# Kinesis-to-Lambda Event Source Mapping with Partial Batch Failure Reporting
resource "aws_lambda_event_source_mapping" "kinesis_scoring_esm" {
  event_source_arn                   = var.kinesis_stream_arn
  function_name                      = aws_lambda_function.scoring_consumer.arn
  starting_position                  = "LATEST"
  batch_size                         = 100
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
}

# -----------------------------------------------------------------------------
# 5. Amazon CloudWatch: Monitoring & Operational Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "lambda_scoring_errors" {
  alarm_name          = "${var.project_name}-lambda-scoring-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alarm when FinGuard fraud scoring Lambda encounters high execution errors"

  dimensions = {
    FunctionName = aws_lambda_function.scoring_consumer.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_scoring_throttles" {
  alarm_name          = "${var.project_name}-lambda-scoring-throttles-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alarm when FinGuard fraud scoring Lambda experiences concurrency throttling"

  dimensions = {
    FunctionName = aws_lambda_function.scoring_consumer.function_name
  }
}

