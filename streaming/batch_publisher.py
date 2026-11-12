"""
Batch publisher implementing PutRecords with partial-failure retry and backoff.
"""
import time
import logging
from typing import Any, Dict, List, Tuple
from streaming.config import KinesisStreamConfig
from streaming.retry import BackoffPolicy
from streaming.dlq import FailedRecordQuarantine
from streaming.metrics import StreamingMetricsTracker

logger = logging.getLogger(__name__)


class KinesisBatchPublisher:
    """Publishes transaction record batches to Amazon Kinesis with partial retry handling."""

    def __init__(
        self,
        kinesis_client: Any,
        config: KinesisStreamConfig,
        metrics: StreamingMetricsTracker,
        quarantine: FailedRecordQuarantine,
    ):
        self.client = kinesis_client
        self.config = config
        self.metrics = metrics
        self.quarantine = quarantine
        self.backoff = BackoffPolicy(
            base_delay=config.base_backoff_sec,
            max_delay=config.max_backoff_sec
        )

    def publish_batch(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Publishes a list of records (up to 500) to Kinesis.
        Retries partial failures up to config.max_attempts.
        Returns (success_count, final_failed_count).
        """
        if not records:
            return 0, 0

        # Calculate payload byte size for telemetry
        batch_bytes = sum(len(r["Data"]) for r in records)
        start_time = time.time()

        records_to_send = list(records)
        attempt = 1
        successful_count = 0
        failed_count = 0

        while records_to_send and attempt <= self.config.max_attempts:
            # Prepare request payload (remove internal tracking keys)
            kinesis_payload = [
                {"Data": r["Data"], "PartitionKey": r["PartitionKey"]}
                for r in records_to_send
            ]

            try:
                response = self.client.put_records(
                    StreamName=self.config.stream_name,
                    Records=kinesis_payload
                )

                response_records = response.get("Records", [])
                failed_indices = []

                for idx, result in enumerate(response_records):
                    if "ErrorCode" in result:
                        failed_indices.append(idx)
                    else:
                        successful_count += 1

                if not failed_indices:
                    # Entire batch succeeded
                    records_to_send = []
                    break

                # Prepare list of failed records for the next retry attempt
                failed_records = [records_to_send[i] for i in failed_indices]
                logger.warning(
                    f"PutRecords partial failure: {len(failed_records)}/{len(records_to_send)} records failed. "
                    f"Retrying (Attempt {attempt}/{self.config.max_attempts})."
                )

                records_to_send = failed_records
                attempt += 1

                if attempt <= self.config.max_attempts:
                    self.backoff.sleep(attempt)

            except Exception as exc:
                logger.error(f"Kinesis PutRecords API exception: {str(exc)}")
                attempt += 1
                if attempt <= self.config.max_attempts:
                    self.backoff.sleep(attempt)

        # Handle any records that exhausted all retries
        if records_to_send:
            failed_count = len(records_to_send)
            for r in records_to_send:
                self.quarantine.quarantine_record(
                    record_payload={"origin_id": r.get("_origin_id"), "PartitionKey": r.get("PartitionKey")},
                    error_code="MAX_RETRIES_EXCEEDED",
                    error_message=f"Exhausted {self.config.max_attempts} attempts during PutRecords"
                )

        elapsed = time.time() - start_time
        self.metrics.record_batch(successful_count, failed_count, batch_bytes, elapsed)

        return successful_count, failed_count

