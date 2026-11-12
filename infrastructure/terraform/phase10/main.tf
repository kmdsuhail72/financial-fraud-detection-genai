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
      Project     = "FinGuard-AI"
      Phase       = "Phase-10-Security-RBAC"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ========================================================
# Amazon Cognito User Pool for Fraud Ops Identity
# ========================================================
resource "aws_cognito_user_pool" "fraud_analysts" {
  name = "${var.project_name}-${var.environment}-analysts-user-pool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  schema {
    attribute_data_type      = "String"
    name                     = "email"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 128
    }
  }

  schema {
    attribute_data_type      = "String"
    name                     = "role"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 3
      max_length = 32
    }
  }
}

# ========================================================
# Cognito App Client (SPA PKCE Grant Flow - No Client Secret)
# ========================================================
resource "aws_cognito_user_pool_client" "analyst_portal_client" {
  name         = "${var.project_name}-${var.environment}-portal-client"
  user_pool_id = aws_cognito_user_pool.fraud_analysts.id

  generate_secret                      = false
  explicit_auth_flows                  = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_CUSTOM_AUTH"
  ]
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile", "aws.cognito.signin.user.admin"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls
  supported_identity_providers         = ["COGNITO"]
  prevent_user_existence_errors        = "ENABLED"

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
}

# ========================================================
# Cognito User Pool Groups (RBAC Tiers)
# ========================================================
resource "aws_cognito_user_group" "admin" {
  name         = "Admin"
  user_pool_id = aws_cognito_user_pool.fraud_analysts.id
  description  = "Super Administrator with full case, user, and audit access"
  precedence   = 1
}

resource "aws_cognito_user_group" "investigator" {
  name         = "Investigator"
  user_pool_id = aws_cognito_user_pool.fraud_analysts.id
  description  = "Senior Fraud Investigator authorized to assign, resolve, and take binding action"
  precedence   = 10
}

resource "aws_cognito_user_group" "analyst" {
  name         = "Analyst"
  user_pool_id = aws_cognito_user_pool.fraud_analysts.id
  description  = "Tier-1 Fraud Analyst authorized to review, append notes, and escalate"
  precedence   = 20
}

resource "aws_cognito_user_group" "auditor" {
  name         = "Auditor"
  user_pool_id = aws_cognito_user_pool.fraud_analysts.id
  description  = "Compliance and Audit Officer with read-only case and audit log privileges"
  precedence   = 30
}

# ========================================================
# DynamoDB Security Audit Log Table
# ========================================================
resource "aws_dynamodb_table" "security_audit" {
  name         = var.audit_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "actor_email"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "ActorEmailIndex"
    hash_key        = "actor_email"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = var.audit_table_name
  }
}

