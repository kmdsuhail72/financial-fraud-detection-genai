"""
Normal Banking Transaction Generator.
Simulates legitimate consumer and corporate payment transactions with realistic diurnal patterns.
"""
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from transaction_simulator.config import (
    CITIES_INDIA, MERCHANT_CATEGORIES, DEFAULT_SIMULATION_START
)


class NormalTransactionGenerator:
    """Generates realistic legitimate banking transactions."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_single(
        self,
        transaction_id: str,
        account: Dict,
        customer: Dict,
        customer_devices: List[Dict],
        merchants: List[Dict],
        current_time: datetime
    ) -> Dict:
        # Choose merchant
        merchant = self.rng.choice(merchants)
        category = merchant["merchant_category"]
        cat_info = MERCHANT_CATEGORIES[category]

        # Log-normal transaction amount centered around category average
        mu = math.log(cat_info["avg_amount"])
        sigma = 0.55
        raw_amount = self.rng.lognormvariate(mu, sigma)
        amount = round(max(20.0, min(raw_amount, 250000.0)), 2)

        # Payment channel & transaction type alignment
        if category in ["GROCERY", "DINING"]:
            txn_type = self.rng.choice(["CARD_PAYMENT", "UPI_TRANSFER"])
            channel = "POS" if txn_type == "CARD_PAYMENT" else "MOBILE"
        elif category in ["ELECTRONICS", "JEWELRY", "TRAVEL"]:
            txn_type = self.rng.choice(["CARD_PAYMENT", "ONLINE_BANKING", "UPI_TRANSFER"])
            channel = "WEB" if txn_type == "ONLINE_BANKING" else ("POS" if txn_type == "CARD_PAYMENT" else "MOBILE")
        elif category == "UTILITIES":
            txn_type = "ONLINE_BANKING"
            channel = "WEB"
        else:
            txn_type = self.rng.choice(["UPI_TRANSFER", "WIRE_TRANSFER"])
            channel = "MOBILE"

        # Device Selection (Use known registered device)
        if customer_devices:
            device = self.rng.choice(customer_devices)
            device_id = device["device_id"]
            ip_address = device["primary_ip"]
        else:
            device_id = f"DEV-{self.rng.randint(40001, 49999):05d}"
            ip_address = f"192.0.2.{self.rng.randint(2, 250)}"

        # Location: 94% home city, 6% domestic travel
        if self.rng.random() < 0.94:
            city = customer["city"]
        else:
            city = self.rng.choice([c["city"] for c in CITIES_INDIA])

        return {
            "transaction_id": transaction_id,
            "account_id": account["account_id"],
            "customer_id": customer["customer_id"],
            "transaction_type": txn_type,
            "amount": amount,
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "merchant_category": category,
            "transaction_timestamp": current_time.isoformat(),
            "channel": channel,
            "location": {
                "country": "IN",
                "city": city
            },
            "device_id": device_id,
            "ip_address": ip_address,
            "is_international": False
        }
