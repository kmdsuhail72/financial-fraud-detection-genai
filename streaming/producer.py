"""
High-throughput Kinesis Transaction Producer CLI & Engine.
Streams JSONL transaction records to Amazon Kinesis with automated batching and retries.
"""
import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from streaming.config import KinesisStreamConfig
from streaming.serializer import TransactionSerializer
from streaming.batch_publisher import KinesisBatchPublisher
from streaming.dlq import FailedRecordQuarantine
from streaming.metrics import StreamingMetricsTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kinesis-producer")


class MockKinesisClient:
    """Mock Kinesis client for local testing and dry-run verification."""

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate

    def put_records(self, StreamName: str, Records: List[Dict]):
        out_records = []
        for i, rec in enumerate(Records):
            out_records.append({
                "SequenceNumber": f"seq-{int(time.time()*1000)}-{i}",
                "ShardId": "shardId-000000000000"
            })
        return {"FailedRecordCount": 0, "Records": out_records}


class TransactionStreamProducer:
    """Orchestrates streaming of synthetic transaction files to Amazon Kinesis."""

    def __init__(
        self,
        config: KinesisStreamConfig,
        dry_run: bool = False,
    ):
        self.config = config
        self.dry_run = dry_run
        self.metrics = StreamingMetricsTracker()
        self.quarantine = FailedRecordQuarantine(config.dlq_path)

        # Initialize Boto3 Kinesis client or Mock
        if dry_run:
            logger.info("Operating in DRY-RUN mode. Using MockKinesisClient.")
            self.kinesis_client = MockKinesisClient()
        else:
            try:
                client_kwargs = {"region_name": config.region_name}
                if config.endpoint_url:
                    client_kwargs["endpoint_url"] = config.endpoint_url
                self.kinesis_client = boto3.client("kinesis", **client_kwargs)
                # Quick call to verify client connectivity
                self.kinesis_client.describe_stream_summary(StreamName=config.stream_name)
                logger.info(f"Connected to live Amazon Kinesis stream: {config.stream_name} ({config.region_name})")
            except (NoCredentialsError, PartialCredentialsError) as e:
                logger.warning(f"AWS credentials not detected: {e}. Falling back to dry-run mock mode.")
                self.kinesis_client = MockKinesisClient()
            except Exception as e:
                logger.warning(f"Live Kinesis connection failed ({e}). Proceeding in simulation mock mode.")
                self.kinesis_client = MockKinesisClient()

        self.publisher = KinesisBatchPublisher(
            kinesis_client=self.kinesis_client,
            config=self.config,
            metrics=self.metrics,
            quarantine=self.quarantine,
        )

    def stream_jsonl_file(self, input_file: str) -> Dict:
        """
        Reads a JSONL file line-by-line and pushes batches to Kinesis.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input transaction file not found: {input_file}")

        logger.info(f"Starting transaction streaming from {input_file} (Batch Size: {self.config.batch_size})")

        current_batch: List[Dict[str, Any]] = []

        with open(input_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue

                try:
                    raw_txn = json.loads(clean_line)
                except json.JSONDecodeError as err:
                    self.quarantine.quarantine_record(clean_line, "JSON_PARSE_ERROR", str(err))
                    continue

                is_valid, record_payload, error_msg = TransactionSerializer.validate_and_serialize(raw_txn)
                if not is_valid:
                    self.quarantine.quarantine_record(raw_txn, "VALIDATION_ERROR", error_msg)
                    continue

                current_batch.append(record_payload)

                if len(current_batch) >= self.config.batch_size:
                    success, failed = self.publisher.publish_batch(current_batch)
                    print(f"Batch complete: success={success} failed={failed}")
                    current_batch = []

            # Flush remaining records
            if current_batch:
                success, failed = self.publisher.publish_batch(current_batch)
                print(f"Batch complete: success={success} failed={failed}")

        summary = self.metrics.summary()
        print(f"Publishing finished: success={summary['successful_records']} failed={summary['failed_records']}")
        return summary


def main():
    parser = argparse.ArgumentParser(description="FinGuard AI — Kinesis Transaction Stream Producer")
    parser.add_argument("--input", type=str, default="data/generated/transactions.jsonl", help="Input JSONL path")
    parser.add_argument("--region", type=str, default="ap-south-1", help="AWS region (default: ap-south-1)")
    parser.add_argument("--stream", type=str, default="finguard-transactions-dev", help="Kinesis stream name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch record count per PutRecords call (max 500)")
    parser.add_argument("--max-attempts", type=int, default=5, help="Maximum retry attempts on partial failures")
    parser.add_argument("--dry-run", action="store_true", help="Force mock publishing without live AWS calls")

    args = parser.parse_args()

    config = KinesisStreamConfig(
        region_name=args.region,
        stream_name=args.stream,
        batch_size=args.batch_size,
        max_attempts=args.max_attempts,
    )

    producer = TransactionStreamProducer(config=config, dry_run=args.dry_run)
    summary = producer.stream_jsonl_file(args.input)

    logger.info("Streaming Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

