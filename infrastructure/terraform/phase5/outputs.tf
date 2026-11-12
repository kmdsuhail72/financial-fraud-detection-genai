output "data_lake_bucket" {
  value = aws_s3_bucket.data_lake.bucket
}

output "glue_database" {
  value = module.glue.database_name
}

output "glue_etl_job" {
  value = module.glue.job_name
}

output "glue_crawler" {
  value = module.glue.crawler_name
}

output "athena_workgroup" {
  value = module.athena.workgroup_name
}
