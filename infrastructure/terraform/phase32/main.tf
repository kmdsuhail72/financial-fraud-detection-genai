# Phase 32 — AWS API Gateway HTTP API, Microservices Security & Access Logging

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_apigatewayv2_api" "finguard_gateway" {
  name          = "${var.environment}-finguard-api-gateway"
  protocol_type = "HTTP"
  description   = "FinGuard AI Enterprise API Gateway for versioned /api/v1 routing, tenant isolation, and microservices security"

  cors_configuration {
    allow_credentials = true
    allow_headers     = ["Authorization", "Content-Type", "X-Request-ID", "X-Service-Key", "X-Tenant-ID"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = var.allowed_origins
    max_age           = 3600
  }

  tags = {
    Environment = var.environment
    Service     = "finguard-api-gateway"
    Phase       = "32"
  }
}

resource "aws_cloudwatch_log_group" "gateway_access_logs" {
  name              = "/aws/apigateway/${var.environment}-finguard-api-gateway-access"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Service     = "finguard-api-gateway"
  }
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.finguard_gateway.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.gateway_access_logs.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit  = var.throttling_rate_limit
    detailed_metrics_enabled = true
  }

  tags = {
    Environment = var.environment
  }
}
