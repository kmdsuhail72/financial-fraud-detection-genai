"""
AWS Lambda Transaction Processor Handler.
Orchestrates Kinesis event decoding, validation, deduplication, feature engineering, and S3 sink.
"""
import os
import logging
from typing import Any, Dict, List
import boto3

from lambda_app.decoder import KinesisRecordDecoder
from lambda_app.validator import TransactionValidator
from lambda_app.idempotency import IdempotencyService
from lambda_app.feature_store import CustomerFeatureStore
from lambda_app.sqs_quarantine import SQSQuarantineService
from lambda_app.s3_sink import S3ProcessedSink

logger = logging.getLogger("finguard-lambda")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Initialize AWS clients lazily or globally
_s3_client = None
_dynamo_client = None
_sqs_client = None


def get_clients():
    global _s3_client, _dynamo_client, _sqs_client
    region = os.getenv("AWS_REGION", "ap-south-1")
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=region)
    if _dynamo_client is None:
        _dynamo_client = boto3.client("dynamodb", region_name=region)
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs", region_name=region)
    return _s3_client, _dynamo_client, _sqs_client


def process_kinesis_records(
    records: List[Dict[str, Any]],
    s3_sink: S3ProcessedSink,
    idempotency_service: IdempotencyService,
    feature_store: CustomerFeatureStore,
    quarantine_service: SQSQuarantineService,
) -> List[Dict[str, str]]:
    """
    Processes records in batch and returns list of failed sequence numbers for partial batch retry.
    """
    batch_item_failures: List[Dict[str, str]] = []

    for record in records:
        seq_num = record.get("kinesis", {}).get("sequenceNumber", record.get("eventID", ""))

        try:
            # 1. Decode Kinesis Record
            is_decoded, payload, seq_num_decoded, decode_error = KinesisRecordDecoder.decode_record(record)
            if not is_decoded:
                logger.warning(f"Decoding failed for record {seq_num}: {decode_error}")
                quarantine_service.quarantine(
                    raw_payload=record.get("kinesis", {}).get("data", ""),
                    error_code="DECODE_ERROR",
                    error_message=decode_error,
                    sequence_number=seq_num
                )
                continue

            # 2. Validate Transaction Schema & Rules
            is_valid, val_code, val_error = TransactionValidator.validate(payload)
            if not is_valid:
                logger.warning(f"Validation failed for record {seq_num} ({val_code}): {val_error}")
                quarantine_service.quarantine(
                    raw_payload=payload,
                    error_code=val_code,
                    error_message=val_error,
                    sequence_number=seq_num
                )
                continue

            txn_id = payload["transaction_id"]
            cust_id = payload["customer_id"]

            # 3. Idempotency Check (Deduplication)
            is_new, idemp_err = idempotency_service.check_and_set_processed(txn_id)
            if not is_new:
                logger.info(f"Transaction {txn_id} is a duplicate; skipping downstream processing.")
                continue

            # 4. Feature Engineering
            cust_state = feature_store.get_customer_state(cust_id)
            features, updated_state = feature_store.compute_features(payload, cust_state)

            # 5. Build Enriched Event
            enriched_event = dict(payload)
            enriched_event["features"] = features
            enriched_event["processing_version"] = "phase4-v1"

            # 6. Store to S3 Processed Data Lake
            s3_sink.store_enriched_transaction(enriched_event)

            # 7. Update Customer State in DynamoDB
            feature_store.save_customer_state(updated_state)

        except Exception as exc:
            logger.error(f"Transient error processing record {seq_num}: {str(exc)}", exc_info=True)
            # Add to partial batch failures so Kinesis retries only this item
            batch_item_failures.append({"itemIdentifier": seq_num})

    return batch_item_failures


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda main handler entrypoint.
    Configured with Event Source Mapping ReportBatchItemFailures.
    """
    records = event.get("Records", [])
    logger.info(f"Lambda invoked with {len(records)} Kinesis records")

    processed_bucket = os.getenv("PROCESSED_BUCKET_NAME", "finguard-data-processed-dev")
    idempotency_table = os.getenv("IDEMPOTENCY_TABLE_NAME", "finguard-idempotency-dev")
    customer_state_table = os.getenv("CUSTOMER_STATE_TABLE_NAME", "finguard-customer-state-dev")
    sqs_queue_url = os.getenv("SQS_QUARANTINE_URL", "")

    s3_client, dynamo_client, sqs_client = get_clients()

    s3_sink = S3ProcessedSink(s3_client, bucket_name=processed_bucket)
    idempotency_service = IdempotencyService(dynamo_client, table_name=idempotency_table)
    feature_store = CustomerFeatureStore(dynamo_client, table_name=customer_state_table)
    quarantine_service = SQSQuarantineService(sqs_client, queue_url=sqs_queue_url)

    failures = process_kinesis_records(
        records=records,
        s3_sink=s3_sink,
        idempotency_service=idempotency_service,
        feature_store=feature_store,
        quarantine_service=quarantine_service
    )

    logger.info(f"Batch processing completed. Failures to retry: {len(failures)}/{len(records)}")
    return {"batchItemFailures": failures}
