"""
Unit tests for Dead-Letter Queue (DLQ) quarantine logging.
"""
import json
import os
import shutil
import tempfile
from streaming.dlq import FailedRecordQuarantine


def test_quarantine_logging():
    temp_dir = tempfile.mkdtemp()
    dlq_file = os.path.join(temp_dir, "quarantine.jsonl")

    try:
        quarantine = FailedRecordQuarantine(dlq_path=dlq_file)
        assert quarantine.count_quarantined() == 0

        quarantine.quarantine_record(
            record_payload={"txn_id": "TXN-FAIL-01"},
            error_code="THROTTLED",
            error_message="Provisioned throughput exceeded after 5 retries"
        )

        assert quarantine.count_quarantined() == 1

        with open(dlq_file, "r", encoding="utf-8") as f:
            line = f.readline()
            entry = json.loads(line)
            assert entry["error_code"] == "THROTTLED"
            assert entry["record"]["txn_id"] == "TXN-FAIL-01"
    finally:
        shutil.rmtree(temp_dir)
