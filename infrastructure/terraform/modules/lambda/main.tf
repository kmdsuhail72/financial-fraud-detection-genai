data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name               = "${var.project_name}-lambda-exec-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_policy_doc" {
  # CloudWatch Logging
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  # Kinesis Streaming Ingestion
  statement {
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
      "kinesis:ListShards",
      "kinesis:ListStreams",
      "kinesis:SubscribeToShard"
    ]
    resources = [var.kinesis_stream_arn]
  }

  # DynamoDB Idempotency & Feature State
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem"
    ]
    resources = [
      var.idempotency_table_arn,
      var.customer_state_table_arn
    ]
  }

  # S3 Processed Data Lake
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject"
    ]
    resources = ["${var.processed_bucket_arn}/*"]
  }

  # SQS Quarantine Queue
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage"
    ]
    resources = [var.sqs_quarantine_arn]
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name   = "${var.project_name}-lambda-policy-${var.environment}"
  policy = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Dummy package zip for initial provisioning
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"
  source {
    content  = "def lambda_handler(event, context): return {'batchItemFailures': []}"
    filename = "handler.py"
  }
}

# Lambda Processor Function
resource "aws_lambda_function" "transaction_processor" {
  function_name    = "${var.project_name}-transaction-processor-${var.environment}"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_app.handler.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      AWS_REGION                 = var.aws_region
      PROCESSED_BUCKET_NAME      = var.processed_bucket_name
      IDEMPOTENCY_TABLE_NAME     = var.idempotency_table_name
      CUSTOMER_STATE_TABLE_NAME  = var.customer_state_table_name
      SQS_QUARANTINE_URL         = var.sqs_quarantine_url
      LOG_LEVEL                  = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-transaction-processor-${var.environment}"
    Environment = var.environment
  }
}

# Event Source Mapping (Kinesis to Lambda)
resource "aws_lambda_event_source_mapping" "kinesis_esm" {
  event_source_arn                   = var.kinesis_stream_arn
  function_name                      = aws_lambda_function.transaction_processor.arn
  starting_position                  = "LATEST"
  batch_size                         = 100
  maximum_batching_window_in_seconds = 1
  bisect_batch_on_function_error     = true
  maximum_retry_attempts             = 3
  function_response_types            = ["ReportBatchItemFailures"]
}

# CloudWatch Alarm: Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Triggers when Lambda transaction processor encounters invocation errors"

  dimensions = {
    FunctionName = aws_lambda_function.transaction_processor.function_name
  }
}

