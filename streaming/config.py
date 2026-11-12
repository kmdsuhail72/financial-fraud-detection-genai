"""
Configuration and constants for Amazon Kinesis streaming pipeline.
"""
import os
from dataclasses import dataclass


@dataclass
class KinesisStreamConfig:
    region_name: str = os.getenv("AWS_REGION", "ap-south-1")
    stream_name: str = os.getenv("KINESIS_STREAM_NAME", "finguard-transactions-dev")
    batch_size: int = int(os.getenv("KINESIS_BATCH_SIZE", "100"))
    max_batch_size: int = 500  # Kinesis PutRecords limit
    max_payload_bytes: int = 5 * 1024 * 1024  # 5 MB Kinesis batch limit
    max_attempts: int = int(os.getenv("KINESIS_MAX_ATTEMPTS", "5"))
    base_backoff_sec: float = 0.2
    max_backoff_sec: float = 5.0
    dlq_path: str = os.getenv("KINESIS_DLQ_PATH", "data/quarantine/failed_transactions.jsonl")
    checkpoint_file: str = os.getenv("KINESIS_CHECKPOINT_FILE", "data/checkpoints/kinesis_consumer.json")
    endpoint_url: str = os.getenv("AWS_ENDPOINT_URL", "")  # Optional LocalStack endpoint
