# Glue Catalog Database
resource "aws_glue_catalog_database" "data_lake_db" {
  name        = "${var.project_name}_data_lake_${var.environment}"
  description = "FinGuard AI Data Lake Database (${var.environment})"
}

# IAM Role for AWS Glue
data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_service_role" {
  name               = "${var.project_name}-glue-service-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

# Glue IAM Policy
data "aws_iam_policy_document" "glue_policy_doc" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      var.data_lake_bucket_arn,
      "${var.data_lake_bucket_arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "glue:*",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "glue_policy" {
  name   = "${var.project_name}-glue-policy-${var.environment}"
  policy = data.aws_iam_policy_document.glue_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "glue_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_policy.arn
}

# Glue PySpark ETL Job
resource "aws_glue_job" "transactions_etl" {
  name         = "${var.project_name}-transactions-etl-${var.environment}"
  role_arn     = aws_iam_role.glue_service_role.arn
  glue_version = "4.0"
  worker_type  = "G.1X"
  number_of_workers = 2
  timeout      = 60

  command {
    script_location = "s3://${var.data_lake_bucket_name}/scripts/glue_jobs/raw_to_processed.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--continuous-log-logGroup"          = "/aws-glue/jobs/${var.project_name}-transactions-etl"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--BRONZE_S3_PATH"                   = "s3://${var.data_lake_bucket_name}/bronze/transactions/"
    "--SILVER_S3_PATH"                   = "s3://${var.data_lake_bucket_name}/silver/transactions/"
  }

  tags = {
    Name        = "${var.project_name}-transactions-etl-${var.environment}"
    Environment = var.environment
  }
}

# Glue Crawler for Silver Data Lake
resource "aws_glue_crawler" "lake_crawler" {
  database_name = aws_glue_catalog_database.data_lake_db.name
  name          = "${var.project_name}-lake-crawler-${var.environment}"
  role          = aws_iam_role.glue_service_role.arn

  s3_target {
    path = "s3://${var.data_lake_bucket_name}/silver/transactions/"
  }

  tags = {
    Name        = "${var.project_name}-lake-crawler-${var.environment}"
    Environment = var.environment
  }
}
