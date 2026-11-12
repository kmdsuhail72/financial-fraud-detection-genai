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
      Phase       = "Phase8"
    }
  }
}

# -----------------------------------------------------------------------------
# 1. DynamoDB: Investigation Cases & Audit Trail
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "investigation_cases" {
  name         = "${var.project_name}-investigation-cases-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "case_id"

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "transaction_id"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "TransactionIndex"
    hash_key        = "transaction_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-investigation-cases-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# 2. AWS Lambda: Case Orchestrator
# -----------------------------------------------------------------------------
resource "aws_iam_role" "case_orchestrator_role" {
  name = "${var.project_name}-case-orchestrator-role-${var.environment}"

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

resource "aws_iam_policy" "case_orchestrator_policy" {
  name = "${var.project_name}-case-orchestrator-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.investigation_alerts_queue_arn
      },
      {
        Sid    = "DynamoDBCases"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.investigation_cases.arn,
          "${aws_dynamodb_table.investigation_cases.arn}/index/*"
        ]
      },
      {
        Sid    = "BedrockConverse"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:Converse"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "case_orchestrator_attach" {
  role       = aws_iam_role.case_orchestrator_role.name
  policy_arn = aws_iam_policy.case_orchestrator_policy.arn
}

data "archive_file" "case_orchestrator_dummy" {
  type        = "zip"
  output_path = "${path.module}/case_orchestrator_dummy.zip"

  source {
    content  = "def lambda_handler(event, context): return {'batchItemFailures': []}"
    filename = "handler.py"
  }
}

resource "aws_lambda_function" "case_orchestrator" {
  function_name    = "${var.project_name}-case-orchestrator-${var.environment}"
  role             = aws_iam_role.case_orchestrator_role.arn
  handler          = "lambda_case_orchestrator.handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512
  filename         = data.archive_file.case_orchestrator_dummy.output_path
  source_code_hash = data.archive_file.case_orchestrator_dummy.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE_CASES = aws_dynamodb_table.investigation_cases.name
      BEDROCK_MODEL_ID     = var.bedrock_model_id
      AWS_REGION           = var.aws_region
    }
  }
}

# SQS-to-Lambda Event Source Mapping
resource "aws_lambda_event_source_mapping" "sqs_case_trigger" {
  event_source_arn        = var.investigation_alerts_queue_arn
  function_name           = aws_lambda_function.case_orchestrator.arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}
