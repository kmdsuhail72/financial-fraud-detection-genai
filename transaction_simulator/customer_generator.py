"""
Synthetic Customer Generator for FinGuard AI Simulator.
Generates realistic customer demographics, risk segments, and geographic profiles.
"""
import random
from typing import Dict, List
from transaction_simulator.config import (
    CITIES_INDIA, FIRST_NAMES, LAST_NAMES, RISK_SEGMENTS
)


class CustomerGenerator:
    """Generates synthetic banking customers."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, count: int) -> List[Dict]:
        customers = []
        city_pool = [c["city"] for c in CITIES_INDIA]
        city_weights = [c["weight"] for c in CITIES_INDIA]

        for i in range(1, count + 1):
            customer_id = f"CUS-{200000 + i:06d}"
            first_name = self.rng.choice(FIRST_NAMES)
            last_name = self.rng.choice(LAST_NAMES)
            city = self.rng.choices(city_pool, weights=city_weights, k=1)[0]
            
            # Risk segment distribution: 70% STANDARD, 20% LOW, 10% HIGH_NET_WORTH
            risk_segment = self.rng.choices(
                RISK_SEGMENTS, weights=[0.20, 0.70, 0.10], k=1
            )[0]

            email = f"{first_name.lower()}.{last_name.lower()}{i % 999}@example-bank.test"
            phone = f"+9198{self.rng.randint(10000000, 99999999)}"

            customer = {
                "customer_id": customer_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "risk_segment": risk_segment,
                "kyc_status": "VERIFIED",
                "country": "IN",
                "city": city,
                "created_at": "2025-01-15T00:00:00Z"
            }
            customers.append(customer)

        return customers

