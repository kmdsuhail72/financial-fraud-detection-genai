resource "aws_sqs_queue" "invalid_transactions_queue" {
  name                      = "${var.project_name}-invalid-transactions-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = {
    Name        = "${var.project_name}-invalid-transactions-${var.environment}"
    Environment = var.environment
  }
}
