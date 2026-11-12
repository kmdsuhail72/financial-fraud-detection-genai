output "model_bucket_name" {
  description = "Name of the S3 bucket storing ML model artifacts"
  value       = aws_s3_bucket.model_artifacts.id
}

output "model_bucket_arn" {
  description = "ARN of the S3 bucket storing ML model artifacts"
  value       = aws_s3_bucket.model_artifacts.arn
}

output "sagemaker_role_arn" {
  description = "ARN of the SageMaker execution role"
  value       = aws_iam_role.sagemaker_role.arn
}
