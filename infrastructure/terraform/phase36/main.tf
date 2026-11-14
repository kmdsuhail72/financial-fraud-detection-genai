# Terraform Module for FinGuard AI Phase 36 — CloudWatch Logs, Alarms & SRE Dashboards
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

# CloudWatch Log Group for FinGuard EKS Microservices
resource "aws_cloudwatch_log_group" "finguard_services_logs" {
  name              = "/aws/eks/finguard/services"
  retention_in_days = var.log_retention_days

  tags = {
    Environment = var.environment
    Project     = "FinGuard-AI"
    ManagedBy   = "Terraform"
    Phase       = "36-Observability"
  }
}

# SNS Topic for SRE Incident Alerts
resource "aws_sns_topic" "sre_alerts" {
  name = "finguard-sre-incident-alerts-${var.environment}"

  tags = {
    Environment = var.environment
    Team        = "SRE"
  }
}

# CloudWatch Metric Alarm for High 5xx Error Rate (> 1%)
resource "aws_cloudwatch_metric_alarm" "high_5xx_error_rate" {
  alarm_name          = "FinGuard-${var.environment}-High5xxErrorRate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xxErrorRate"
  namespace           = "FinGuard/Production"
  period              = 60
  statistic           = "Average"
  threshold           = 1.0 # 1% error rate threshold
  alarm_description   = "Triggered when 5xx HTTP error rate exceeds 1% across microservices."
  alarm_actions       = [aws_sns_topic.sre_alerts.arn]

  dimensions = {
    ClusterName = var.cluster_name
  }
}

# CloudWatch Metric Alarm for P95 Latency Breach (> 200ms)
resource "aws_cloudwatch_metric_alarm" "high_p95_latency" {
  alarm_name          = "FinGuard-${var.environment}-P95LatencyBreach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "FraudScoringLatencyP95"
  namespace           = "FinGuard/Production"
  period              = 60
  statistic           = "Average"
  threshold           = 200.0 # 200 milliseconds
  alarm_description   = "Triggered when fraud scoring p95 latency exceeds 200ms."
  alarm_actions       = [aws_sns_topic.sre_alerts.arn]

  dimensions = {
    ClusterName = var.cluster_name
    ServiceName = "fraud-scoring-service"
  }
}

# CloudWatch SRE Golden Signals Dashboard
resource "aws_cloudwatch_dashboard" "finguard_sre_dashboard" {
  dashboard_name = "FinGuard-SRE-Observability-${var.environment}"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinGuard/Production", "RequestCount", "ClusterName", var.cluster_name],
            [".", "5xxErrorCount", ".", "."]
          ]
          period = 60
          stat   = "Sum"
          region = var.aws_region
          title  = "Request Volume vs 5xx Failures"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinGuard/Production", "FraudScoringLatencyP95", "ClusterName", var.cluster_name]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Fraud Scoring p95 Latency (Target < 200ms)"
          yAxis = {
            left = { min = 0, max = 500 }
          }
        }
      }
    ]
  })
}

