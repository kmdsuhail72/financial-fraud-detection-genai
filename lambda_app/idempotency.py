"""
DynamoDB Idempotency Service.
Guarantees exactly-once transaction processing semantics using conditional writes.
"""
import time
import logging
from typing import Any, Tuple
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class IdempotencyService:
    """Manages transaction deduplication against Amazon DynamoDB."""

    def __init__(self, dynamodb_client: Any, table_name: str = "finguard-idempotency-dev", ttl_days: int = 7):
        self.client = dynamodb_client
        self.table_name = table_name
        self.ttl_seconds = ttl_days * 86400

    def check_and_set_processed(self, transaction_id: str) -> Tuple[bool, str]:
        """
        Attempts to write transaction_id to DynamoDB with conditional check.
        Returns (is_new, error_message).
        - is_new = True: Transaction has never been processed before.
        - is_new = False: Duplicate transaction detected.
        """
        now_epoch = int(time.time())
        expires_at = now_epoch + self.ttl_seconds

        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={
                    "transaction_id": {"S": transaction_id},
                    "processed_at": {"N": str(now_epoch)},
                    "ttl": {"N": str(expires_at)},
                    "status": {"S": "PROCESSING"}
                },
                ConditionExpression="attribute_not_exists(transaction_id)"
            )
            return True, ""
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                logger.info(f"Duplicate transaction skipped by idempotency check: {transaction_id}")
                return False, "DUPLICATE_TRANSACTION"
            logger.error(f"DynamoDB idempotency error for {transaction_id}: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in idempotency service for {transaction_id}: {str(e)}")
            raise e

