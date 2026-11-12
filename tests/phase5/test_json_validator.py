"""
Unit tests for Bronze JSON validation script.
"""
import json
import os
import shutil
import tempfile
from scripts.phase5.validate_json import validate_json_directory


def test_validator_with_valid_and_invalid_data():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a valid file
        valid_file = os.path.join(temp_dir, "valid.json")
        valid_record = {
            "transaction_id": "TXN-VALID-1",
            "account_id": "ACC-01",
            "customer_id": "CUS-01",
            "amount": 5000.0,
            "currency": "INR",
            "channel": "MOBILE",
            "transaction_timestamp": "2026-11-12T10:00:00Z",
            "features": {"new_device_flag": 0}
        }
        with open(valid_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_record) + "\n")

        # Create an invalid file (missing amount and corrupted line)
        invalid_file = os.path.join(temp_dir, "invalid.json")
        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"transaction_id": "TXN-NO-AMOUNT"}) + "\n")
            f.write("{ malformed json line\n")

        total_files, valid_count, errors = validate_json_directory(temp_dir)

        assert total_files == 2
        assert valid_count == 1
        assert len(errors) == 2  # missing fields and malformed json
    finally:
        shutil.rmtree(temp_dir)
