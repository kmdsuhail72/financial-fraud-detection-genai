"""
AWS Glue PySpark ETL Job: Bronze Raw JSON -> Silver Parquet.
Validates schema, flattens structures, deduplicates by transaction_id, and writes partitioned Parquet.
"""
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, year, month, dayofmonth, to_timestamp

# Resolve Glue job arguments
args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "BRONZE_S3_PATH",
    "SILVER_S3_PATH"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

bronze_path = args["BRONZE_S3_PATH"]
silver_path = args["SILVER_S3_PATH"]

# 1. Read Bronze JSON
raw_df = spark.read.json(bronze_path)

# 2. Extract and Flatten Nested Structures
flattened_df = raw_df.select(
    col("transaction_id"),
    col("account_id"),
    col("customer_id"),
    col("transaction_type"),
    col("amount").cast("double"),
    col("currency"),
    col("merchant_id"),
    col("merchant_category"),
    col("channel"),
    col("device_id"),
    col("ip_address"),
    col("is_international").cast("boolean"),
    col("transaction_timestamp"),
    col("location.country").alias("location_country"),
    col("location.city").alias("location_city"),
    col("features.transaction_count_5m_prior").alias("feat_transaction_count_5m_prior"),
    col("features.transaction_count_1h_prior").alias("feat_transaction_count_1h_prior"),
    col("features.average_amount_1h_prior").alias("feat_average_amount_1h_prior"),
    col("features.amount_vs_prior_average").alias("feat_amount_vs_prior_average"),
    col("features.new_device_flag").alias("feat_new_device_flag"),
    col("features.home_city_mismatch").alias("feat_home_city_mismatch"),
    col("features.is_international").alias("feat_is_international"),
    col("features.amount_log1p").alias("feat_amount_log1p"),
    col("processing_version")
)

# 3. Filter Malformed Rows and Deduplicate
valid_df = flattened_df.filter(
    (col("transaction_id").isNotNull()) &
    (col("amount") > 0) &
    (col("transaction_timestamp").isNotNull())
)

deduped_df = valid_df.dropDuplicates(["transaction_id"])

# 4. Generate Partitioning Columns from Timestamp
timestamp_col = to_timestamp(col("transaction_timestamp"))
partitioned_df = deduped_df.withColumn("year", year(timestamp_col)) \
                           .withColumn("month", month(timestamp_col)) \
                           .withColumn("day", dayofmonth(timestamp_col))

# 5. Write Partitioned Parquet with Snappy Compression
partitioned_df.write \
    .partitionBy("year", "month", "day") \
    .mode("append") \
    .option("compression", "snappy") \
    .parquet(silver_path)

job.commit()

