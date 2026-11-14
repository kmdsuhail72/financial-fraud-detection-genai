output "api_gateway_id" {
  description = "ID of the FinGuard HTTP API Gateway"
  value       = aws_apigatewayv2_api.finguard_gateway.id
}

output "api_gateway_endpoint" {
  description = "Base API Gateway invocation URL"
  value       = aws_apigatewayv2_api.finguard_gateway.api_endpoint
}

output "cloudwatch_log_group_arn" {
  description = "ARN of CloudWatch access log group"
  value       = aws_cloudwatch_log_group.gateway_access_logs.arn
}
