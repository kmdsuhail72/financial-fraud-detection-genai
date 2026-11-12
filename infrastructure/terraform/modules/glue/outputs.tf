output "database_name" {
  value = aws_glue_catalog_database.data_lake_db.name
}

output "job_name" {
  value = aws_glue_job.transactions_etl.name
}

output "crawler_name" {
  value = aws_glue_crawler.lake_crawler.name
}

