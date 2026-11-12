"""
AWS Glue PySpark ETL Job: Silver Parquet -> Gold Curated Marts.
Aggregates cleaned transactions into daily, merchant, and channel analytical marts.
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, count, sum as spark_sum, avg, max as spark_max

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "SILVER_S3_PATH",
    "GOLD_S3_PATH"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

silver_path = args["SILVER_S3_PATH"]
gold_path = args["GOLD_S3_PATH"].rstrip("/")

silver_df = spark.read.parquet(silver_path)

# 1. Daily Analytics Mart
daily_summary = silver_df.groupBy("year", "month", "day").agg(
    count("transaction_id").alias("total_transactions"),
    spark_sum("amount").alias("total_volume_inr"),
    avg("amount").alias("average_amount"),
    spark_max("amount").alias("max_amount"),
    spark_sum("feat_new_device_flag").alias("new_device_transactions")
)

daily_summary.write \
    .mode("overwrite") \
    .option("compression", "snappy") \
    .parquet(f"{gold_path}/daily_summary/")

# 2. Channel Performance Mart
channel_summary = silver_df.groupBy("channel").agg(
    count("transaction_id").alias("transaction_count"),
    spark_sum("amount").alias("total_volume"),
    avg("amount").alias("average_ticket")
)

channel_summary.write \
    .mode("overwrite") \
    .option("compression", "snappy") \
    .parquet(f"{gold_path}/channel_summary/")

job.commit()

