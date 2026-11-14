"""
FinGuard AI — Enterprise Locust Load & Stress Testing Scenario
Simulates concurrent synthetic transaction traffic, fraud scoring requests,
and analyst case investigation queries.
Usage:
    locust -f locust/locustfile.py --host http://127.0.0.1:8000
    locust -f locust/locustfile.py --headless -u 100 -r 10 --run-time 1m --host http://127.0.0.1:8000
"""
from __future__ import annotations

import random
import time
from locust import HttpUser, between, events, task


class FinGuardLoadUser(HttpUser):
    """Simulates realistic concurrent banking client and internal analyst workloads."""

    wait_time = between(0.05, 0.25)  # 50ms to 250ms simulated user think time

    @task(10)
    def probe_health(self) -> None:
        """Lightweight high-frequency health & liveness check."""
        self.client.get("/health", name="/health")

    @task(8)
    def score_fraud_transaction(self) -> None:
        """Simulates real-time transaction scoring inference."""
        txn_id = f"txn-locust-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        payload = {
            "transaction_id": txn_id,
            "features": {
                "amount": round(random.uniform(100.0, 75000.0), 2),
                "currency": "INR",
                "channel": random.choice(["UPI", "IMPS", "NEFT", "CARD"]),
                "transaction_count_5m_prior": random.randint(1, 8),
                "transaction_count_1h_prior": random.randint(3, 20),
                "new_device_flag": random.choice([True, False]),
                "home_city_mismatch": random.choice([True, False]),
                "is_international": random.choice([False, False, True]),
            },
        }
        with self.client.post("/score", json=payload, name="/score", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Scoring failed with HTTP {response.status_code}")

    @task(3)
    def query_cases_queue(self) -> None:
        """Simulates operations analyst case queue queries."""
        self.client.get("/investigations/cases?limit=25", name="/investigations/cases")

    @task(2)
    def scrape_metrics(self) -> None:
        """Simulates Prometheus scraper pulling exposition metrics."""
        self.client.get("/metrics", headers={"Accept": "text/plain"}, name="/metrics")

    @task(1)
    def query_dr_health(self) -> None:
        """Simulates operational disaster recovery health probe."""
        self.client.get("/dr/health", name="/dr/health")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Logs test initialization parameters."""
    print("=" * 70)
    print(" FinGuard AI — Locust Performance Engine Initialized")
    print(f" Target Host: {environment.host}")
    print("=" * 70)
