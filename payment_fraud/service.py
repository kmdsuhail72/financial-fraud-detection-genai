"""
FinGuard AI — Phase 29: Payment Fraud Service Layer.
Coordinates payment evaluation, history retrieval, and metrics.
"""
from __future__ import annotations

from typing import List, Optional

from payment_fraud.models import (
    PaymentAssessmentResponse,
    PaymentEvent,
    PaymentMetrics,
)
from payment_fraud.store import PaymentFraudStore, payment_store


class PaymentFraudService:
    def __init__(self, store: Optional[PaymentFraudStore] = None):
        self.store = store or payment_store

    def assess_payment(self, payment: PaymentEvent) -> PaymentAssessmentResponse:
        return self.store.record_and_assess(payment)

    def get_assessment(self, transaction_id: str) -> Optional[PaymentAssessmentResponse]:
        return self.store.get_assessment(transaction_id)

    def list_assessments(self, limit: int = 50) -> List[PaymentAssessmentResponse]:
        return self.store.list_assessments(limit=limit)

    def get_metrics(self) -> PaymentMetrics:
        return self.store.get_metrics()


# Default singleton instance
payment_service = PaymentFraudService()

