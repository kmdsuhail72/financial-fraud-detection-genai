"""
FinGuard AI — Phase 29: In-Memory Payment Event & Assessment Store.
Thread-safe store for payment transactions, rolling 10-minute velocity tracking,
and historical assessment records.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from payment_fraud.engine import evaluate_payment_risk
from payment_fraud.models import (
    AlertAction,
    PaymentAssessmentResponse,
    PaymentDeviceContext,
    PaymentEvent,
    PaymentMetrics,
    PaymentRail,
    RiskLevel,
)


class PaymentFraudStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._events: Dict[str, PaymentEvent] = {}
        self._assessments: Dict[str, PaymentAssessmentResponse] = {}
        self._customer_txn_times: Dict[str, List[datetime]] = {}
        self._seed_default_data()

    def _seed_default_data(self):
        """Seeds benchmark demo transactions and assessments."""
        now = datetime.now(timezone.utc)

        # 1. Benchmark Example (45/100 MEDIUM, REVIEW)
        benchmark_event = PaymentEvent(
            transaction_id="TXN-2026-UPI-285000",
            customer_id="CUST-BLR-40291",
            amount=285000.0,
            currency="INR",
            payment_rail=PaymentRail.UPI,
            sender_account="ACC-SB-991203",
            beneficiary_account="ACC-HDFC-882194",
            beneficiary_name="Apex Digital Services",
            is_new_beneficiary=True,
            customer_home_city="Bengaluru",
            transaction_city="Mumbai",
            is_international=False,
            device_context=PaymentDeviceContext(
                device_id="DEV-ANDROID-SM-G998B",
                ip_address="49.36.120.45",
                user_agent="Mozilla/5.0 (Linux; Android 14; SM-G998B) UPI/4.2",
                location="Mumbai, MH, IN",
            ),
            timestamp=now - timedelta(minutes=5),
        )
        self.record_and_assess(benchmark_event)

        # 2. Low-Risk Payment (0/100 LOW, MONITOR)
        low_risk_event = PaymentEvent(
            transaction_id="TXN-2026-NEFT-15000",
            customer_id="CUST-DEL-10294",
            amount=15000.0,
            currency="INR",
            payment_rail=PaymentRail.NEFT,
            sender_account="ACC-ICICI-110294",
            beneficiary_account="ACC-SBI-440192",
            beneficiary_name="Metro Electric Utilities",
            is_new_beneficiary=False,
            customer_home_city="Delhi",
            transaction_city="Delhi",
            is_international=False,
            device_context=PaymentDeviceContext(
                device_id="DEV-IOS-IPHONE15-01",
                ip_address="122.161.44.12",
                location="Delhi, DL, IN",
            ),
            timestamp=now - timedelta(minutes=25),
        )
        self.record_and_assess(low_risk_event)

        # 3. High-Risk Payment (80/100 HIGH, PRIORITY_REVIEW)
        high_risk_event = PaymentEvent(
            transaction_id="TXN-2026-RTGS-750000",
            customer_id="CUST-HYD-55102",
            amount=750000.0,
            currency="USD",
            payment_rail=PaymentRail.RTGS,
            sender_account="ACC-HDFC-991023",
            beneficiary_account="ACC-BARCLAYS-GB-441029",
            beneficiary_name="Global Offshore Holdings Ltd",
            is_new_beneficiary=True,
            customer_home_city="Hyderabad",
            transaction_city="London",
            is_international=True,
            device_context=None,
            timestamp=now - timedelta(minutes=1),
        )
        self.record_and_assess(high_risk_event)

    def get_recent_10m_count(self, customer_id: str, current_time: datetime) -> int:
        """Counts prior transactions for this customer within rolling 10-minute window."""
        with self._lock:
            timestamps = self._customer_txn_times.get(customer_id, [])
            cutoff = current_time - timedelta(minutes=10)
            valid = [t for t in timestamps if t >= cutoff and t < current_time]
            return len(valid)

    def record_and_assess(self, payment: PaymentEvent) -> PaymentAssessmentResponse:
        """Stores payment event, evaluates risk, and updates velocity trackers."""
        with self._lock:
            event_time = payment.timestamp or datetime.now(timezone.utc)
            # Count transactions in rolling 10-minute window
            recent_count = self.get_recent_10m_count(payment.customer_id, event_time)

            assessment = evaluate_payment_risk(payment, recent_10m_txn_count=recent_count)

            # Persist event and assessment
            self._events[payment.transaction_id] = payment
            self._assessments[payment.transaction_id] = assessment

            if payment.customer_id not in self._customer_txn_times:
                self._customer_txn_times[payment.customer_id] = []
            self._customer_txn_times[payment.customer_id].append(event_time)

            return assessment

    def get_assessment(self, transaction_id: str) -> Optional[PaymentAssessmentResponse]:
        with self._lock:
            return self._assessments.get(transaction_id)

    def get_event(self, transaction_id: str) -> Optional[PaymentEvent]:
        with self._lock:
            return self._events.get(transaction_id)

    def list_assessments(self, limit: int = 50) -> List[PaymentAssessmentResponse]:
        with self._lock:
            items = list(self._assessments.values())
            items.sort(key=lambda x: x.assessed_at, reverse=True)
            return items[:limit]

    def get_metrics(self) -> PaymentMetrics:
        with self._lock:
            assessments = list(self._assessments.values())
            events = list(self._events.values())

            total = len(assessments)
            if total == 0:
                return PaymentMetrics(
                    total_assessed=0,
                    monitor_count=0,
                    review_count=0,
                    priority_review_count=0,
                    avg_risk_score=0.0,
                    high_value_count=0,
                    new_beneficiary_count=0,
                    city_mismatch_count=0,
                    velocity_flagged_count=0,
                    international_count=0,
                )

            monitor = sum(1 for a in assessments if a.action == AlertAction.MONITOR)
            review = sum(1 for a in assessments if a.action == AlertAction.REVIEW)
            priority = sum(1 for a in assessments if a.action == AlertAction.PRIORITY_REVIEW)
            avg_score = sum(a.risk_score for a in assessments) / float(total)

            high_val = sum(1 for e in events if e.amount >= 200000.0)
            new_ben = sum(1 for e in events if e.is_new_beneficiary)
            mismatch = sum(
                1
                for e in events
                if e.customer_home_city
                and e.transaction_city
                and e.customer_home_city.strip().lower() != e.transaction_city.strip().lower()
            )
            intl = sum(1 for e in events if e.is_international or (e.currency and e.currency.upper() != "INR"))
            velocity_cnt = sum(
                1
                for a in assessments
                if any(s.category == "Velocity" for s in a.signals)
            )

            return PaymentMetrics(
                total_assessed=total,
                monitor_count=monitor,
                review_count=review,
                priority_review_count=priority,
                avg_risk_score=round(avg_score, 1),
                high_value_count=high_val,
                new_beneficiary_count=new_ben,
                city_mismatch_count=mismatch,
                velocity_flagged_count=velocity_cnt,
                international_count=intl,
            )


# Global singleton instance
payment_store = PaymentFraudStore()

