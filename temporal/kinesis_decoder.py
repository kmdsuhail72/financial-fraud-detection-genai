"""AWS Lambda & Kinesis Streaming Event Decoder with Idempotent Deduplication."""

from __future__ import annotations

import base64
import json
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from temporal.models import TemporalTransactionEvent

logger = logging.getLogger("finguard-kinesis-decoder")


class KinesisLambdaDecoder:
    """Decodes Kinesis batches and enforces idempotent sliding deduplication."""

    def __init__(self, max_cache_size: int = 10000):
        self.max_cache_size = max_cache_size
        self._seen_transactions: OrderedDict[str, float] = OrderedDict()

    def is_duplicate(self, tx_id: str) -> bool:
        """Checks if transaction has already been processed."""
        return tx_id in self._seen_transactions

    def mark_seen(self, tx_id: str, timestamp: float) -> None:
        """Records transaction into bounded sliding window cache."""
        self._seen_transactions[tx_id] = timestamp
        if len(self._seen_transactions) > self.max_cache_size:
            self._seen_transactions.popitem(last=False)

    def decode_kinesis_event(
        self,
        event: Dict[str, Any],
    ) -> Tuple[List[TemporalTransactionEvent], int, int]:
        """
        Parses standard AWS Lambda Kinesis event structure:
        event = {"Records": [{"kinesis": {"data": "<base64>", "sequenceNumber": "..."}}]}
        Returns:
            (valid_events, duplicate_count, error_count)
        """
        records = event.get("Records", [])
        valid_events: List[TemporalTransactionEvent] = []
        dup_count = 0
        err_count = 0

        for rec in records:
            k_payload = rec.get("kinesis", {})
            raw_data = k_payload.get("data", "")
            try:
                if isinstance(raw_data, str):
                    decoded_str = base64.b64decode(raw_data).decode("utf-8")
                else:
                    decoded_str = raw_data.decode("utf-8")

                data_dict = json.loads(decoded_str)
                tx_id = data_dict.get("transaction_id") or data_dict.get("id")
                if not tx_id:
                    err_count += 1
                    continue

                if self.is_duplicate(tx_id):
                    dup_count += 1
                    continue

                # Parse into model
                parsed_event = TemporalTransactionEvent(
                    transaction_id=tx_id,
                    timestamp=float(data_dict.get("timestamp", 0.0)),
                    source_account=data_dict.get("source_account", data_dict.get("account_id", "")),
                    target_account=data_dict.get("target_account"),
                    customer_id=data_dict.get("customer_id"),
                    device_id=data_dict.get("device_id"),
                    ip_address=data_dict.get("ip_address"),
                    merchant_id=data_dict.get("merchant_id"),
                    amount=float(data_dict.get("amount", 0.0)),
                    currency=data_dict.get("currency", "USD"),
                    channel=data_dict.get("channel", "mobile"),
                    event_type=data_dict.get("event_type", "TRANSFER"),
                    is_fraud=data_dict.get("is_fraud"),
                )

                self.mark_seen(tx_id, parsed_event.timestamp)
                valid_events.append(parsed_event)
            except Exception as exc:
                logger.warning("Failed to decode Kinesis record: %s", exc)
                err_count += 1

        return valid_events, dup_count, err_count

    def clear_cache(self) -> None:
        """Clears deduplication cache for testing."""
        self._seen_transactions.clear()

