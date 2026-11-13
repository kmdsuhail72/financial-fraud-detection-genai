"""Phase 20 — Decision Orchestration Service."""

from __future__ import annotations

import logging
from typing import List, Optional

from decision.engine import RiskFusionEngine
from decision.models import (
    DecisionRequest,
    FraudClassification,
    FraudDecisionResponse,
    RiskPolicyConfig,
    RiskPriority,
)
from decision.store import DecisionStore

logger = logging.getLogger("finguard-decision-service")


class DecisionService:
    """Singleton service for real-time risk fusion and decision persistence."""

    _instance: Optional[DecisionService] = None

    def __init__(
        self,
        engine: Optional[RiskFusionEngine] = None,
        store: Optional[DecisionStore] = None,
    ):
        self.engine = engine or RiskFusionEngine()
        self.store = store or DecisionStore()

    @classmethod
    def get_instance(cls) -> DecisionService:
        if cls._instance is None:
            cls._instance = DecisionService()
        return cls._instance

    def evaluate_transaction(self, request: DecisionRequest) -> FraudDecisionResponse:
        """Evaluates transaction risk idempotently."""
        # 1. Idempotent check
        existing = self.store.get_by_transaction_id(request.transaction_id)
        if existing:
            return existing

        # 2. Multi-signal evaluation
        decision = self.engine.evaluate(request)

        # 3. Store reference record
        stored = self.store.save_decision(decision)
        return stored

    def get_decision(self, decision_id: str) -> Optional[FraudDecisionResponse]:
        return self.store.get_decision(decision_id)

    def list_decisions(
        self,
        priority: Optional[RiskPriority] = None,
        classification: Optional[FraudClassification] = None,
        limit: int = 50,
    ) -> List[FraudDecisionResponse]:
        return self.store.list_decisions(priority=priority, classification=classification, limit=limit)

    def get_active_policy(self) -> RiskPolicyConfig:
        return self.engine.policy

    def update_active_policy(self, policy: RiskPolicyConfig) -> RiskPolicyConfig:
        return self.engine.update_policy(policy)


def get_decision_service() -> DecisionService:
    return DecisionService.get_instance()

