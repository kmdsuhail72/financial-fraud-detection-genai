"""Phase 20 — Idempotent In-Memory Decision Store with Reference Persistence Interface."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Dict, List, Optional

from decision.models import FraudClassification, FraudDecisionResponse, RiskPriority

logger = logging.getLogger("finguard-decision-store")


class DecisionStore:
    """
    Idempotent reference decision storage.
    Enforces deduplication per transaction_id and provides indexing by priority and classification.
    """

    def __init__(self, max_records: int = 5000):
        self.max_records = max_records
        self._by_id: OrderedDict[str, FraudDecisionResponse] = OrderedDict()
        self._by_transaction_id: Dict[str, str] = {}

    def save_decision(self, decision: FraudDecisionResponse) -> FraudDecisionResponse:
        """
        Saves decision. If transaction_id was already evaluated, returns existing stored decision (idempotency).
        """
        tx_id = decision.transaction_id
        if tx_id in self._by_transaction_id:
            existing_id = self._by_transaction_id[tx_id]
            logger.info("Transaction %s already evaluated. Returning existing decision %s", tx_id, existing_id)
            return self._by_id[existing_id]

        self._by_id[decision.decision_id] = decision
        self._by_transaction_id[tx_id] = decision.decision_id

        if len(self._by_id) > self.max_records:
            old_id, old_dec = self._by_id.popitem(last=False)
            self._by_transaction_id.pop(old_dec.transaction_id, None)

        return decision

    def get_decision(self, decision_id: str) -> Optional[FraudDecisionResponse]:
        return self._by_id.get(decision_id)

    def get_by_transaction_id(self, tx_id: str) -> Optional[FraudDecisionResponse]:
        dec_id = self._by_transaction_id.get(tx_id)
        if dec_id:
            return self._by_id.get(dec_id)
        return None

    def list_decisions(
        self,
        priority: Optional[RiskPriority] = None,
        classification: Optional[FraudClassification] = None,
        limit: int = 50,
    ) -> List[FraudDecisionResponse]:
        results = list(self._by_id.values())
        if priority:
            results = [d for d in results if d.priority == priority]
        if classification:
            results = [d for d in results if d.classification == classification]

        # Reverse chronological
        results.reverse()
        return results[:limit]

    def clear(self) -> None:
        self._by_id.clear()
        self._by_transaction_id.clear()

