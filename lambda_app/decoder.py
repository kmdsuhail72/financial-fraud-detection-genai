"""
Kinesis event decoder for AWS Lambda.
Decodes Base64 data and extracts Kinesis metadata.
"""
import base64
import json
import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class KinesisRecordDecoder:
    """Decodes standard AWS Lambda Kinesis event records."""

    @staticmethod
    def decode_record(record: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str, str]:
        """
        Decodes a single record from a Kinesis Lambda event.
        Returns (is_valid, parsed_json, sequence_number, error_message).
        """
        kinesis_data = record.get("kinesis", {})
        sequence_number = kinesis_data.get("sequenceNumber", record.get("eventID", ""))
        raw_b64 = kinesis_data.get("data")

        if not raw_b64:
            return False, {}, sequence_number, "Missing 'kinesis.data' field in event record"

        try:
            raw_bytes = base64.b64decode(raw_b64)
            json_str = raw_bytes.decode("utf-8")
            payload = json.loads(json_str)
            return True, payload, sequence_number, ""
        except (base64.binascii.Error, UnicodeDecodeError) as err:
            return False, {}, sequence_number, f"Base64 or UTF-8 decode error: {str(err)}"
        except json.JSONDecodeError as err:
            return False, {}, sequence_number, f"Malformed JSON payload: {str(err)}"
        except Exception as err:
            return False, {}, sequence_number, f"Unexpected decoding error: {str(err)}"

