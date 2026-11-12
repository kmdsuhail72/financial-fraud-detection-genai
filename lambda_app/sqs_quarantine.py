"""
Amazon SQS Quarantine Integration for invalid and failed transaction events.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SQSQuarantineService:
    """Sends invalid or corrupted transaction events to an Amazon SQS quarantine queue."""

    def __init__(self, sqs_client: Any, queue_url: str):
        self.client = sqs_client
        self.queue_url = queue_url

    def quarantine(
        self,
        raw_payload: Any,
        error_code: str,
        error_message: str,
        sequence_number: str = ""
    ) -> bool:
        """Sends quarantine message to SQS queue."""
        if not self.queue_url:
            logger.warning(f"No SQS queue URL configured; skipping SQS quarantine for {error_code}: {error_message}")
            return False

        message_body = {
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
            "error_code": error_code,
            "error_message": error_message,
            "sequence_number": sequence_number,
            "raw_payload": raw_payload
        }

        try:
            self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body, default=str),
                MessageAttributes={
                    "ErrorCode": {"DataType": "String", "StringValue": error_code}
                }
            )
            logger.info(f"Quarantined invalid transaction to SQS [{error_code}]: {error_message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send quarantine event to SQS: {str(e)}")
            return False
