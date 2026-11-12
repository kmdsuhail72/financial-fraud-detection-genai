"""
DynamoDB-backed Customer Feature State and Behavioral Feature Engineering.
"""
import math
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CustomerFeatureStore:
    """Computes real-time behavioral features and updates DynamoDB customer state."""

    def __init__(self, dynamodb_client: Any, table_name: str = "finguard-customer-state-dev"):
        self.client = dynamodb_client
        self.table_name = table_name

    def get_customer_state(self, customer_id: str) -> Dict[str, Any]:
        """Retrieves customer historical feature state."""
        try:
            resp = self.client.get_item(
                TableName=self.table_name,
                Key={"customer_id": {"S": customer_id}}
            )
            item = resp.get("Item")
            if not item:
                return {
                    "registered_devices": set(),
                    "home_city": "",
                    "recent_transactions": []
                }

            # Parse devices
            dev_item = item.get("registered_devices", {})
            devices = set(dev_item.get("SS", [])) if "SS" in dev_item else set()

            # Parse home city
            home_city = item.get("home_city", {}).get("S", "")

            # Parse recent transactions
            txns_raw = item.get("recent_transactions", {}).get("L", [])
            recent_txns = []
            for t in txns_raw:
                m = t.get("M", {})
                epoch = int(m.get("epoch", {}).get("N", 0))
                amt = float(m.get("amount", {}).get("N", 0.0))
                recent_txns.append({"epoch": epoch, "amount": amt})

            return {
                "registered_devices": devices,
                "home_city": home_city,
                "recent_transactions": recent_txns
            }
        except ClientError as e:
            logger.warning(f"Could not load state for customer {customer_id}: {str(e)}")
            return {
                "registered_devices": set(),
                "home_city": "",
                "recent_transactions": []
            }

    def compute_features(
        self,
        transaction: Dict[str, Any],
        customer_state: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Computes behavioral features using prior state and prepares updated state.
        Returns (features_dict, updated_state_dict).
        """
        amount = float(transaction["amount"])
        curr_device = str(transaction.get("device_id", ""))
        location = transaction.get("location", {})
        curr_city = location.get("city", "") if isinstance(location, dict) else ""
        curr_country = location.get("country", "IN") if isinstance(location, dict) else "IN"
        is_intl_flag = bool(transaction.get("is_international", False))

        # Parse transaction epoch
        ts_str = str(transaction["transaction_timestamp"]).replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        current_epoch = int(dt.timestamp())

        prior_txns = customer_state["recent_transactions"]

        # 1. Transaction count in last 5 minutes prior
        cutoff_5m = current_epoch - 300
        count_5m = sum(1 for t in prior_txns if t["epoch"] >= cutoff_5m and t["epoch"] <= current_epoch)

        # 2. Transaction count in last 1 hour prior
        cutoff_1h = current_epoch - 3600
        txns_1h = [t for t in prior_txns if t["epoch"] >= cutoff_1h and t["epoch"] <= current_epoch]
        count_1h = len(txns_1h)

        # 3. Average amount in last 1 hour prior
        if txns_1h:
            avg_amount_1h = round(sum(t["amount"] for t in txns_1h) / len(txns_1h), 2)
            amount_vs_avg = round(amount / (avg_amount_1h if avg_amount_1h > 0 else 1.0), 2)
        else:
            avg_amount_1h = round(amount, 2)
            amount_vs_avg = 1.0

        # 4. Device verification
        known_devices = customer_state["registered_devices"]
        new_device_flag = 0 if curr_device in known_devices and len(known_devices) > 0 else 1

        # 5. Location mismatch
        home_city = customer_state.get("home_city")
        if not home_city:
            home_city = curr_city
        home_city_mismatch = 1 if home_city and curr_city and (curr_city != home_city) else 0

        # 6. International flag
        is_international = 1 if is_intl_flag or curr_country != "IN" else 0

        # 7. Amount log1p
        amount_log1p = round(math.log1p(amount), 4)

        features = {
            "transaction_count_5m_prior": count_5m,
            "transaction_count_1h_prior": count_1h,
            "average_amount_1h_prior": avg_amount_1h,
            "amount_vs_prior_average": amount_vs_avg,
            "new_device_flag": new_device_flag,
            "home_city_mismatch": home_city_mismatch,
            "is_international": is_international,
            "amount_log1p": amount_log1p
        }

        # Prepare updated state (prune transactions older than 24 hours)
        cutoff_24h = current_epoch - 86400
        pruned_txns = [t for t in prior_txns if t["epoch"] >= cutoff_24h]
        pruned_txns.append({"epoch": current_epoch, "amount": amount})

        updated_devices = set(known_devices)
        if curr_device:
            updated_devices.add(curr_device)

        updated_state = {
            "customer_id": transaction["customer_id"],
            "registered_devices": updated_devices,
            "home_city": home_city,
            "recent_transactions": pruned_txns
        }

        return features, updated_state

    def save_customer_state(self, updated_state: Dict[str, Any]):
        """Persists updated customer state to DynamoDB."""
        dev_list = list(updated_state["registered_devices"])
        item = {
            "customer_id": {"S": updated_state["customer_id"]},
            "home_city": {"S": updated_state.get("home_city", "")},
            "recent_transactions": {
                "L": [
                    {
                        "M": {
                            "epoch": {"N": str(t["epoch"])},
                            "amount": {"N": str(t["amount"])}
                        }
                    }
                    for t in updated_state["recent_transactions"]
                ]
            }
        }
        if dev_list:
            item["registered_devices"] = {"SS": dev_list}

        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=item
            )
        except Exception as e:
            logger.warning(f"Failed to persist state for customer {updated_state.get('customer_id')}: {str(e)}")
