"""
Dead-Letter Queue (DLQ) / Failed-record quarantine handler for Kinesis.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


class FailedRecordQuarantine:
    """Quarantines unprocessable or exhausted retry records to a durable DLQ file."""

    def __init__(self, dlq_path: str = "data/quarantine/failed_transactions.jsonl"):
        self.dlq_path = dlq_path
        os.makedirs(os.path.dirname(self.dlq_path), exist_ok=True)

    def quarantine_record(self, record_payload: Any, error_code: str, error_message: str):
        """Appends a failed record with failure context to the quarantine log."""
        entry = {
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
            "error_code": error_code,
            "error_message": error_message,
            "record": record_payload if isinstance(record_payload, dict) else str(record_payload)
        }
        with open(self.dlq_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def count_quarantined(self) -> int:
        if not os.path.exists(self.dlq_path):
            return 0
        with open(self.dlq_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

