"""
Feature Engineering Module for Simulator & Real-Time Processing.
Derives behavioral velocity and anomaly features without target leakage.
"""
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple


class FeatureEngineer:
    """
    Computes rolling velocity and behavioral features on an ordered sequence of transactions.
    Ensures zero target leakage: only historical information strictly prior to the current
    transaction timestamp is used to calculate rolling aggregations.
    """

    def __init__(
        self,
        registered_devices: List[Dict],
        customer_accounts: List[Dict],
        merchants: List[Dict],
    ):
        # Index customer registered devices
        self.known_devices: Dict[str, Set[str]] = defaultdict(set)
        for dev in registered_devices:
            self.known_devices[dev["customer_id"]].add(dev["device_id"])

        # Index account ages
        self.account_ages: Dict[str, int] = {
            acc["account_id"]: acc.get("account_age_days", 365)
            for acc in customer_accounts
        }

        # Index merchant risks
        self.merchant_risks: Dict[str, float] = {
            m["merchant_id"]: m.get("merchant_risk", 0.10)
            for m in merchants
        }

        # State tracking for rolling features per account
        # account_id -> list of (timestamp_dt, amount, city, country)
        self.history: Dict[str, List[Tuple[datetime, float, str, str]]] = defaultdict(list)

    def extract_features(
        self,
        transactions: List[Dict],
    ) -> List[Dict]:
        """
        Extracts features for all transactions in temporal order.
        Returns a list of feature dictionaries (predictive variables only).
        """
        # Ensure chronological ordering
        sorted_txns = sorted(
            transactions,
            key=lambda t: datetime.fromisoformat(t["transaction_timestamp"])
        )

        features_list = []

        for txn in sorted_txns:
            txn_id = txn["transaction_id"]
            account_id = txn["account_id"]
            customer_id = txn["customer_id"]
            amount = float(txn["amount"])
            txn_time = datetime.fromisoformat(txn["transaction_timestamp"])
            location = txn.get("location", {})
            curr_city = location.get("city", "")
            curr_country = location.get("country", "IN")
            device_id = txn.get("device_id", "")
            is_intl = bool(txn.get("is_international", False))
            merchant_id = txn.get("merchant_id", "")

            # Prior transaction history for this account
            acc_hist = self.history[account_id]

            # 1. Rolling 24h Average Amount
            cutoff_24h = txn_time.timestamp() - 86400
            recent_24h_amounts = [
                h_amt for h_time, h_amt, _, _ in acc_hist
                if h_time.timestamp() >= cutoff_24h
            ]

            if recent_24h_amounts:
                avg_amount_24h = round(sum(recent_24h_amounts) / len(recent_24h_amounts), 2)
            else:
                # Fallback to category baseline if account has no history today
                avg_amount_24h = round(amount, 2)

            # 2. Transaction Count in Last 5 Minutes
            cutoff_5m = txn_time.timestamp() - 300
            count_5m = sum(1 for h_time, _, _, _ in acc_hist if h_time.timestamp() >= cutoff_5m)

            # 3. Transaction Count in Last 1 Hour
            cutoff_1h = txn_time.timestamp() - 3600
            count_1h = sum(1 for h_time, _, _, _ in acc_hist if h_time.timestamp() >= cutoff_1h)

            # 4. Amount Deviation Ratio (Current amount / 24h baseline)
            baseline = avg_amount_24h if avg_amount_24h > 0 else 1.0
            amount_deviation = round(amount / baseline, 4)

            # 5. New Device Indicator (1 if unseen in known registry, 0 otherwise)
            is_new_device = 0 if device_id in self.known_devices[customer_id] else 1

            # 6. Location Change / Velocity Indicator
            cutoff_2h = txn_time.timestamp() - 7200
            recent_locs = [
                (h_city, h_country) for h_time, _, h_city, h_country in acc_hist
                if h_time.timestamp() >= cutoff_2h
            ]

            location_change = 0
            if recent_locs:
                last_city, last_country = recent_locs[-1]
                if last_country != curr_country or (last_city != curr_city and last_city != ""):
                    location_change = 1

            # 7. International Flag
            intl_flag = 1 if is_intl or curr_country != "IN" else 0

            # 8. Merchant Risk Score
            merchant_risk = self.merchant_risks.get(merchant_id, 0.10)

            # 9. Account Age Days
            account_age_days = self.account_ages.get(account_id, 365)

            feature_record = {
                "transaction_id": txn_id,
                "transaction_amount": amount,
                "avg_amount_24h": avg_amount_24h,
                "transaction_count_5m": count_5m,
                "transaction_count_1h": count_1h,
                "amount_deviation": amount_deviation,
                "new_device": is_new_device,
                "location_change": location_change,
                "international_flag": intl_flag,
                "merchant_risk": merchant_risk,
                "account_age_days": account_age_days,
            }
            features_list.append(feature_record)

            # Update account transaction history state
            acc_hist.append((txn_time, amount, curr_city, curr_country))

        return features_list

