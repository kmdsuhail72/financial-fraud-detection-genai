"""
Event serializer, validator, and partition key selector for Kinesis records.
"""
import json
from typing import Any, Dict, Tuple


class TransactionSerializer:
    """Serializes transaction payloads into Kinesis-compatible PutRecords entries."""

    REQUIRED_FIELDS = [
        "transaction_id",
        "account_id",
        "customer_id",
        "amount",
        "transaction_timestamp",
        "currency",
        "channel",
    ]

    @classmethod
    def validate_and_serialize(cls, transaction: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """
        Validates required fields and encodes to UTF-8 bytes.
        Returns (is_valid, kinesis_record, error_message).
        """
        # 1. Validation
        missing = [f for f in cls.REQUIRED_FIELDS if f not in transaction]
        if missing:
            return False, {}, f"Missing required transaction fields: {missing}"

        # 2. Extract partition key (account_id preserves transaction order per account)
        partition_key = str(transaction.get("account_id"))
        if not partition_key:
            partition_key = str(transaction.get("transaction_id", "default-partition"))

        try:
            # 3. Serialize to UTF-8 bytes
            json_str = json.dumps(transaction, default=str)
            raw_bytes = json_str.encode("utf-8")

            kinesis_record = {
                "Data": raw_bytes,
                "PartitionKey": partition_key,
                "_origin_id": transaction.get("transaction_id")  # metadata for tracking
            }
            return True, kinesis_record, ""
        except (TypeError, ValueError) as err:
            return False, {}, f"JSON serialization failed: {str(err)}"

    @classmethod
    def deserialize(cls, raw_data: bytes) -> Tuple[bool, Dict[str, Any], str]:
        """
        Decodes raw bytes retrieved from Kinesis GetRecords into a Python dict.
        """
        try:
            decoded = json.loads(raw_data.decode("utf-8"))
            return True, decoded, ""
        except Exception as err:
            return False, {}, f"Deserialization error: {str(err)}"
