-- 1. Create Analytics Database
CREATE DATABASE IF NOT EXISTS finguard_data_lake_dev
COMMENT 'FinGuard AI Banking Fraud Analytics Database'
LOCATION 's3://YOUR-UNIQUE-BUCKET-NAME/silver/';

-- 2. External Table: Cleaned Silver Transactions
CREATE EXTERNAL TABLE IF NOT EXISTS finguard_data_lake_dev.transactions_silver (
    transaction_id STRING,
    account_id STRING,
    customer_id STRING,
    transaction_type STRING,
    amount DOUBLE,
    currency STRING,
    merchant_id STRING,
    merchant_category STRING,
    channel STRING,
    device_id STRING,
    ip_address STRING,
    is_international BOOLEAN,
    transaction_timestamp STRING,
    location_country STRING,
    location_city STRING,
    feat_transaction_count_5m_prior INT,
    feat_transaction_count_1h_prior INT,
    feat_average_amount_1h_prior DOUBLE,
    feat_amount_vs_prior_average DOUBLE,
    feat_new_device_flag INT,
    feat_home_city_mismatch INT,
    feat_is_international INT,
    feat_amount_log1p DOUBLE,
    processing_version STRING
)
PARTITIONED BY (
    year INT,
    month INT,
    day INT
)
STORED AS PARQUET
LOCATION 's3://YOUR-UNIQUE-BUCKET-NAME/silver/transactions/'
TBLPROPERTIES (
    'parquet.compression' = 'SNAPPY'
);

-- 3. Recover Partitions
MSCK REPAIR TABLE finguard_data_lake_dev.transactions_silver;

