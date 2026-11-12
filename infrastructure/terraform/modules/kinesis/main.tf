resource "aws_kinesis_stream" "transactions_stream" {
  name             = "${var.project_name}-transactions-${var.environment}"
  retention_period = var.retention_period_hours

  # Support ON_DEMAND mode as specified in Phase 3 architecture
  stream_mode_details {
    stream_mode = var.stream_mode
  }

  shard_count = var.stream_mode == "PROVISIONED" ? var.shard_count : null

  encryption_type = "KMS"
  kms_key_id      = var.kms_key_arn

  enforce_consumer_deletion = true

  tags = {
    Name        = "${var.project_name}-transactions-${var.environment}"
    Environment = var.environment
    Service     = "KinesisDataStreams"
  }
}

# CloudWatch Alarm: PutRecords Failed Records
resource "aws_cloudwatch_metric_alarm" "kinesis_put_records_failed" {
  alarm_name          = "${var.project_name}-kinesis-put-records-failed-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "PutRecords.FailedRecords"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alarm when Kinesis PutRecords experiences record ingestion failures"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions_stream.name
  }
}

# CloudWatch Alarm: Write Provisioned Throughput Exceeded
resource "aws_cloudwatch_metric_alarm" "kinesis_write_exceeded" {
  alarm_name          = "${var.project_name}-kinesis-write-throttling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alarm when stream writes exceed provisioned or on-demand limits"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions_stream.name
  }
}
