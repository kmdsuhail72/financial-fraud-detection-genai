resource "aws_athena_workgroup" "analytics_workgroup" {
  name        = "${var.project_name}-analytics-${var.environment}"
  description = "FinGuard AI Fraud Analytics Athena Workgroup"
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.data_lake_bucket_name}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-analytics-${var.environment}"
    Environment = var.environment
  }
}
