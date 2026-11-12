output "workgroup_name" {
  value = aws_athena_workgroup.analytics_workgroup.name
}

output "workgroup_arn" {
  value = aws_athena_workgroup.analytics_workgroup.arn
}
