"""
Bank Account Generator for Synthetic Customers.
Generates savings, current, and credit card accounts with realistic balances and tenure.
"""
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from transaction_simulator.config import ACCOUNT_TYPES, DEFAULT_SIMULATION_START


class AccountGenerator:
    """Generates bank accounts linked to synthetic customers."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, customers: List[Dict]) -> List[Dict]:
        accounts = []
        account_seq = 100000

        for cust in customers:
            customer_id = cust["customer_id"]
            risk_segment = cust["risk_segment"]

            # Balance distribution based on risk segment
            if risk_segment == "HIGH_NET_WORTH":
                base_balance = self.rng.uniform(500000.0, 5000000.0)
                num_accounts = self.rng.choice([2, 3])
            elif risk_segment == "LOW":
                base_balance = self.rng.uniform(5000.0, 80000.0)
                num_accounts = 1
            else:  # STANDARD
                base_balance = self.rng.uniform(25000.0, 350000.0)
                num_accounts = self.rng.choice([1, 2])

            for a_idx in range(num_accounts):
                account_seq += 1
                account_id = f"ACC-{account_seq:06d}"

                if a_idx == 0:
                    acc_type = "SAVINGS"
                    balance = round(base_balance, 2)
                elif a_idx == 1:
                    acc_type = "CREDIT_CARD"
                    balance = round(self.rng.uniform(50000.0, 300000.0), 2)
                else:
                    acc_type = "CURRENT"
                    balance = round(base_balance * 0.5, 2)

                # Account opening date between 60 and 1000 days prior to simulation start
                opened_days_ago = self.rng.randint(60, 1000)
                opened_date = (DEFAULT_SIMULATION_START - timedelta(days=opened_days_ago)).date().isoformat()

                account = {
                    "account_id": account_id,
                    "customer_id": customer_id,
                    "account_type": acc_type,
                    "balance": balance,
                    "currency": "INR",
                    "status": "ACTIVE",
                    "opened_date": opened_date,
                    "account_age_days": opened_days_ago
                }
                accounts.append(account)

        return accounts

