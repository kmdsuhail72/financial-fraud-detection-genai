provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "FinGuard AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "s3" {
  source       = "../../modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "kinesis" {
  source       = "../../modules/kinesis"
  project_name = var.project_name
  environment  = var.environment
}
