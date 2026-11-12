"""
Fraud Scenario Engine for FinGuard AI Simulator.
Injects 8 controlled financial fraud archetypes into transaction streams.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from transaction_simulator.config import CITIES_INTERNATIONAL, DOC_IP_PREFIXES


class FraudScenarioEngine:
    """Injects 8 distinct banking fraud scenarios into the transaction stream."""

    SCENARIO_NAMES = [
        "CARD_NOT_PRESENT",
        "ACCOUNT_TAKEOVER",
        "TRANSACTION_VELOCITY",
        "UNUSUAL_HIGH_VALUE",
        "GEOGRAPHIC_ANOMALY",
        "NEW_DEVICE_SUSPICIOUS",
        "MERCHANT_SUSPICIOUS",
        "CARD_TESTING_BURST",
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def inject_scenario(
        self,
        scenario_type: str,
        base_txn_id: str,
        account: Dict,
        customer: Dict,
        customer_devices: List[Dict],
        merchants: List[Dict],
        current_time: datetime,
    ) -> List[Tuple[Dict, Dict]]:
        """
        Generates one or more transactions comprising the designated fraud scenario.
        Returns a list of tuples: (transaction_dict, metadata_dict).
        """
        results = []

        if scenario_type == "CARD_NOT_PRESENT":
            # Scenario 1: CNP Fraud - High amount online web purchase with unknown device/IP
            merchant = self._find_merchant_by_category(merchants, ["ELECTRONICS", "JEWELRY", "TRAVEL"])
            amount = round(self.rng.uniform(65000.0, 195000.0), 2)
            ip = f"198.51.100.{self.rng.randint(2, 250)}"
            device_id = f"DEV-ROGUE-{self.rng.randint(1000, 9999)}"

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "CARD_PAYMENT",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": current_time.isoformat(),
                "channel": "WEB",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": device_id,
                "ip_address": ip,
                "is_international": False,
            }
            meta = {
                "scenario": "CARD_NOT_PRESENT",
                "reason": "High-value online card purchase from unrecognized IP and device",
                "severity": "HIGH",
            }
            results.append((txn, meta))

        elif scenario_type == "ACCOUNT_TAKEOVER":
            # Scenario 2: ATO - New device drains 80-95% of available balance
            merchant = self._find_merchant_by_category(merchants, ["TRANSFER", "ELECTRONICS"])
            drain_amount = round(float(account["balance"]) * self.rng.uniform(0.75, 0.95), 2)
            amount = max(80000.0, drain_amount)
            new_dev = f"DEV-ATO-{self.rng.randint(1000, 9999)}"
            new_ip = f"203.0.113.{self.rng.randint(2, 250)}"

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "WIRE_TRANSFER",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": current_time.isoformat(),
                "channel": "MOBILE",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": new_dev,
                "ip_address": new_ip,
                "is_international": False,
            }
            meta = {
                "scenario": "ACCOUNT_TAKEOVER",
                "reason": "Sudden near-total balance drain from brand new device",
                "severity": "CRITICAL",
            }
            results.append((txn, meta))

        elif scenario_type == "TRANSACTION_VELOCITY":
            # Scenario 3: High Velocity - 4-6 rapid transactions within 5 minutes
            burst_count = self.rng.randint(4, 6)
            merchant = self._find_merchant_by_category(merchants, ["TRANSFER", "GROCERY", "ELECTRONICS"])
            device = customer_devices[0] if customer_devices else {"device_id": "DEV-40001", "primary_ip": "192.0.2.1"}

            for idx in range(burst_count):
                txn_id = f"{base_txn_id}-V{idx+1}"
                txn_time = current_time + timedelta(seconds=idx * self.rng.randint(20, 60))
                amount = round(self.rng.uniform(15000.0, 48000.0), 2)

                txn = {
                    "transaction_id": txn_id,
                    "account_id": account["account_id"],
                    "customer_id": customer["customer_id"],
                    "transaction_type": "UPI_TRANSFER",
                    "amount": amount,
                    "currency": "INR",
                    "merchant_id": merchant["merchant_id"],
                    "merchant_category": merchant["merchant_category"],
                    "transaction_timestamp": txn_time.isoformat(),
                    "channel": "MOBILE",
                    "location": {"country": "IN", "city": customer["city"]},
                    "device_id": device["device_id"],
                    "ip_address": device["primary_ip"],
                    "is_international": False,
                }
                meta = {
                    "scenario": "TRANSACTION_VELOCITY",
                    "reason": f"High velocity burst transaction #{idx+1} in 5-minute window",
                    "severity": "HIGH",
                }
                results.append((txn, meta))

        elif scenario_type == "UNUSUAL_HIGH_VALUE":
            # Scenario 4: High Value Spike - 7x to 15x normal transaction average
            merchant = self._find_merchant_by_category(merchants, ["JEWELRY", "ELECTRONICS"])
            amount = round(self.rng.uniform(150000.0, 450000.0), 2)
            device = customer_devices[0] if customer_devices else {"device_id": "DEV-40001", "primary_ip": "192.0.2.1"}

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "CARD_PAYMENT",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": current_time.isoformat(),
                "channel": "POS",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": device["device_id"],
                "ip_address": device["primary_ip"],
                "is_international": False,
            }
            meta = {
                "scenario": "UNUSUAL_HIGH_VALUE",
                "reason": "Single transaction amount substantially exceeds historical customer limit",
                "severity": "CRITICAL",
            }
            results.append((txn, meta))

        elif scenario_type == "GEOGRAPHIC_ANOMALY":
            # Scenario 5: Geographic Anomaly / Impossible Travel (Cross-border foreign transaction)
            intl_city = self.rng.choice(CITIES_INTERNATIONAL)
            merchant = self._find_merchant_by_category(merchants, ["TRAVEL", "JEWELRY", "ELECTRONICS"])
            amount = round(self.rng.uniform(45000.0, 180000.0), 2)
            foreign_ip = f"198.51.100.{self.rng.randint(2, 250)}"

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "CARD_PAYMENT",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": current_time.isoformat(),
                "channel": "POS",
                "location": {"country": intl_city["country"], "city": intl_city["city"]},
                "device_id": f"DEV-INTL-{self.rng.randint(1000, 9999)}",
                "ip_address": foreign_ip,
                "is_international": True,
            }
            meta = {
                "scenario": "GEOGRAPHIC_ANOMALY",
                "reason": f"Foreign transaction in {intl_city['city']} ({intl_city['country']}) indicates impossible travel velocity",
                "severity": "HIGH",
            }
            results.append((txn, meta))

        elif scenario_type == "NEW_DEVICE_SUSPICIOUS":
            # Scenario 6: New Device at Night (02:30 AM)
            merchant = self._find_merchant_by_category(merchants, ["TRANSFER", "ELECTRONICS"])
            amount = round(self.rng.uniform(40000.0, 110000.0), 2)
            night_time = current_time.replace(hour=2, minute=self.rng.randint(15, 55))
            new_dev = f"DEV-UNSEEN-{self.rng.randint(1000, 9999)}"
            new_ip = f"203.0.113.{self.rng.randint(2, 250)}"

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "ONLINE_BANKING",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": night_time.isoformat(),
                "channel": "WEB",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": new_dev,
                "ip_address": new_ip,
                "is_international": False,
            }
            meta = {
                "scenario": "NEW_DEVICE_SUSPICIOUS",
                "reason": "Unseen device access during late-night off-peak hours",
                "severity": "HIGH",
            }
            results.append((txn, meta))

        elif scenario_type == "MERCHANT_SUSPICIOUS":
            # Scenario 7: High-risk merchant category with abnormal transaction
            merchant = self._find_merchant_by_category(merchants, ["JEWELRY"])
            amount = round(self.rng.uniform(85000.0, 220000.0), 2)
            device = customer_devices[0] if customer_devices else {"device_id": "DEV-40001", "primary_ip": "192.0.2.1"}

            txn = {
                "transaction_id": base_txn_id,
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "CARD_PAYMENT",
                "amount": amount,
                "currency": "INR",
                "merchant_id": merchant["merchant_id"],
                "merchant_category": merchant["merchant_category"],
                "transaction_timestamp": current_time.isoformat(),
                "channel": "POS",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": device["device_id"],
                "ip_address": device["primary_ip"],
                "is_international": False,
            }
            meta = {
                "scenario": "MERCHANT_SUSPICIOUS",
                "reason": "Repeated high-value transaction at flagged high-risk merchant",
                "severity": "HIGH",
            }
            results.append((txn, meta))

        else:  # CARD_TESTING_BURST
            # Scenario 8: Multiple micro-transactions (card testing) followed by large withdrawal
            micro_count = self.rng.randint(3, 4)
            grocery_merchant = self._find_merchant_by_category(merchants, ["GROCERY", "UTILITIES"])
            atm_merchant = self._find_merchant_by_category(merchants, ["TRANSFER", "ELECTRONICS"])
            device_id = f"DEV-TESTER-{self.rng.randint(1000, 9999)}"
            test_ip = f"192.0.2.{self.rng.randint(10, 240)}"

            for idx in range(micro_count):
                txn_id = f"{base_txn_id}-TEST{idx+1}"
                txn_time = current_time + timedelta(seconds=idx * 15)
                micro_amt = round(self.rng.uniform(10.0, 65.0), 2)

                txn = {
                    "transaction_id": txn_id,
                    "account_id": account["account_id"],
                    "customer_id": customer["customer_id"],
                    "transaction_type": "CARD_PAYMENT",
                    "amount": micro_amt,
                    "currency": "INR",
                    "merchant_id": grocery_merchant["merchant_id"],
                    "merchant_category": grocery_merchant["merchant_category"],
                    "transaction_timestamp": txn_time.isoformat(),
                    "channel": "WEB",
                    "location": {"country": "IN", "city": customer["city"]},
                    "device_id": device_id,
                    "ip_address": test_ip,
                    "is_international": False,
                }
                meta = {
                    "scenario": "CARD_TESTING_BURST",
                    "reason": f"Card probing micro-transaction #{idx+1}",
                    "severity": "MEDIUM",
                }
                results.append((txn, meta))

            # Immediate large cash-out transaction
            cashout_time = current_time + timedelta(seconds=(micro_count * 15) + 30)
            large_amt = round(self.rng.uniform(90000.0, 240000.0), 2)
            large_txn = {
                "transaction_id": f"{base_txn_id}-CASHOUT",
                "account_id": account["account_id"],
                "customer_id": customer["customer_id"],
                "transaction_type": "ATM_WITHDRAWAL",
                "amount": large_amt,
                "currency": "INR",
                "merchant_id": atm_merchant["merchant_id"],
                "merchant_category": atm_merchant["merchant_category"],
                "transaction_timestamp": cashout_time.isoformat(),
                "channel": "ATM",
                "location": {"country": "IN", "city": customer["city"]},
                "device_id": device_id,
                "ip_address": test_ip,
                "is_international": False,
            }
            meta_large = {
                "scenario": "CARD_TESTING_BURST",
                "reason": "Immediate high-value cashout following verified card testing probe",
                "severity": "CRITICAL",
            }
            results.append((large_txn, meta_large))

        return results

    def _find_merchant_by_category(self, merchants: List[Dict], categories: List[str]) -> Dict:
        matched = [m for m in merchants if m["merchant_category"] in categories]
        if matched:
            return self.rng.choice(matched)
        return self.rng.choice(merchants)
