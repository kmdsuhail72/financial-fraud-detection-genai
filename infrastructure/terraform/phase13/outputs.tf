output "threat_intel_kms_key_arn" {
  value       = aws_kms_key.threat_intel_kms.arn
  description = "KMS Customer Managed Key ARN for threat intelligence encryption."
}

output "threat_intel_bucket_name" {
  value       = aws_s3_bucket.threat_intel_bucket.id
  description = "Name of the S3 archive bucket for threat indicators."
}

output "threat_intel_bucket_arn" {
  value       = aws_s3_bucket.threat_intel_bucket.arn
  description = "ARN of the S3 archive bucket for threat indicators."
}

