"""
Amazon S3 Processed Transaction Storage Sink.
Stores enriched, date-partitioned JSON transactions for downstream machine learning.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


class S3ProcessedSink:
    """Writes enriched transactions to partitioned S3 prefixes."""

    def __init__(self, s3_client: Any, bucket_name: str, prefix: str = "processed/transactions"):
        self.client = s3_client
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

    def store_enriched_transaction(self, enriched_event: Dict[str, Any]) -> str:
        """
        Stores enriched event into partitioned S3 path:
        processed/transactions/year=YYYY/month=MM/day=DD/{transaction_id}.json
        Returns the resulting S3 key.
        """
        txn_id = enriched_event["transaction_id"]
        ts_str = str(enriched_event.get("transaction_timestamp", datetime.now(timezone.utc).isoformat()))
        cleaned_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned_ts)

        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        day = dt.strftime("%d")

        s3_key = f"{self.prefix}/year={year}/month={month}/day={day}/{txn_id}.json"
        body = json.dumps(enriched_event, default=str)

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=body.encode("utf-8"),
                ContentType="application/json"
            )
            logger.info(f"Stored processed transaction to s3://{self.bucket_name}/{s3_key}")
            return s3_key
        except Exception as e:
            logger.error(f"Failed to store enriched transaction {txn_id} to S3: {str(e)}")
            raise e
