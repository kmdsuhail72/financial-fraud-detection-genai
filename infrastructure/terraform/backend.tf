terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  # In production, replace with remote S3 backend
  # backend "s3" {
  #   bucket         = "finguard-terraform-state-ap-south-1"
  #   key            = "environments/dev/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "finguard-tf-locks"
  #   encrypt        = true
  # }
}
