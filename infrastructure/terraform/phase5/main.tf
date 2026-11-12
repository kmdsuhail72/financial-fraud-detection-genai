terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "FinGuard AI"
      Environment = var.environment
      Phase       = "Phase5-DataLake"
      ManagedBy   = "Terraform"
    }
  }
}

# Medallion Data Lake S3 Bucket
resource "aws_s3_bucket" "data_lake" {
  bucket        = var.data_lake_bucket_name
  force_destroy = var.environment == "dev" ? true : false
}

resource "aws_s3_bucket_versioning" "data_lake_versioning" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake_encryption" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Glue Resources (Catalog, ETL Job, Crawler)
module "glue" {
  source                = "../modules/glue"
  project_name          = var.project_name
  environment           = var.environment
  data_lake_bucket_name = aws_s3_bucket.data_lake.bucket
  data_lake_bucket_arn  = aws_s3_bucket.data_lake.arn
}

# Athena Workgroup
module "athena" {
  source                = "../modules/athena"
  project_name          = var.project_name
  environment           = var.environment
  data_lake_bucket_name = aws_s3_bucket.data_lake.bucket
}

