"""AWS Lambda — Real-Time Graph Event Processor for Amazon Neptune (Phase 16).

Consumes transaction streams from Amazon Kinesis Data Streams,
validates events, applies idempotency checks, resolves entities,
and synchronizes relationship edges into the Amazon Neptune graph database.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

from graph.neptune_client import get_neptune_client
from graph.relationship_sync import RelationshipSyncEngine

logger = logging.getLogger("finguard-lambda-graph-sync")
logger.setLevel(logging.INFO)

# Global engine instance for warm Lambda container reuse
SYNC_ENGINE: Optional[RelationshipSyncEngine] = None


def get_sync_engine() -> RelationshipSyncEngine:
    global SYNC_ENGINE
    if SYNC_ENGINE is None:
        client = get_neptune_client()
        SYNC_ENGINE = RelationshipSyncEngine(client=client)
    return SYNC_ENGINE


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for Kinesis Data Streams graph synchronization.
    Supports Kinesis partial batch failure reporting.
    """
    records = event.get("Records", [])
    logger.info("Processing batch of %d Kinesis records for Neptune sync.", len(records))

    engine = get_sync_engine()
    batch_item_failures: List[Dict[str, str]] = []
    processed_count = 0
    duplicate_count = 0

    for record in records:
        sequence_number = record.get("kinesis", {}).get("sequenceNumber", "unknown")
        try:
            # 1. Decode base64 payload from Kinesis
            raw_data = record.get("kinesis", {}).get("data", "")
            if isinstance(raw_data, str):
                payload_str = base64.b64decode(raw_data).decode("utf-8")
            else:
                payload_str = raw_data.decode("utf-8")

            payload = json.loads(payload_str)

            # 2. Synchronize into Neptune Graph
            result = engine.sync_transaction_event(payload)

            if result.get("status") == "DUPLICATE_SKIPPED":
                duplicate_count += 1
            else:
                processed_count += 1

        except Exception as exc:
            logger.error("Failed to process Kinesis record %s: %s", sequence_number, exc, exc_info=True)
            batch_item_failures.append({"itemIdentifier": sequence_number})

    logger.info(
        "Neptune sync complete: %d synchronized, %d duplicates skipped, %d failed.",
        processed_count,
        duplicate_count,
        len(batch_item_failures),
    )

    return {
        "statusCode": 200,
        "batchItemFailures": batch_item_failures,
        "stats": {
            "processed": processed_count,
            "duplicates": duplicate_count,
            "failed": len(batch_item_failures),
        },
    }

