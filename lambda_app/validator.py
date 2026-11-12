"""
Transaction schema and business rule validator.
"""
from datetime import datetime
from typing import Any, Dict, Tuple


class TransactionValidator:
    """Validates structural constraints and business rules on decoded transactions."""

    REQUIRED_FIELDS = [
        "transaction_id",
        "account_id",
        "customer_id",
        "amount",
        "currency",
        "transaction_timestamp",
        "channel",
    ]

    @classmethod
    def validate(cls, txn: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Validates the incoming transaction dictionary.
        Returns (is_valid, error_code, error_message).
        """
        # 1. Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in txn or txn[field] is None:
                return False, "MISSING_REQUIRED_FIELD", f"Field '{field}' is required and cannot be null"

        # 2. Validate Amount
        try:
            amount = float(txn["amount"])
            if amount <= 0:
                return False, "INVALID_AMOUNT", f"Amount must be strictly greater than 0, received: {amount}"
        except (ValueError, TypeError):
            return False, "INVALID_AMOUNT_TYPE", f"Amount must be numeric, received: {type(txn['amount'])}"

        # 3. Validate Timestamp
        ts_str = str(txn["transaction_timestamp"])
        try:
            # Handle ISO timestamps with Z or offset
            cleaned_ts = ts_str.replace("Z", "+00:00")
            datetime.fromisoformat(cleaned_ts)
        except ValueError:
            return False, "INVALID_TIMESTAMP", f"Invalid ISO 8601 timestamp: '{ts_str}'"

        # 4. Validate Currency
        currency = str(txn.get("currency", ""))
        if len(currency) != 3:
            return False, "INVALID_CURRENCY", f"Currency code must be 3 characters, received: '{currency}'"

        return True, "", ""
