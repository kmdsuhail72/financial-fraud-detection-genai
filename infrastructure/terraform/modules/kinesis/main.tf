variable "project_name" { type = string }
variable "environment" { type = string }

resource "aws_kinesis_stream" "transactions_stream" {
  name             = "${var.project_name}-transactions-${var.environment}"
  shard_count      = 2
  retention_period = 168 # 7 days

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name = "${var.project_name}-transactions-${var.environment}"
  }
}

output "stream_name" {
  value = aws_kinesis_stream.transactions_stream.name
}

output "stream_arn" {
  value = aws_kinesis_stream.transactions_stream.arn
}
