"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) Service.
Singleton coordinator for transaction monitoring, customer profiling, AML cases, and SAR drafts.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from aml.models import (
    AMLAlert,
    AMLCaseStatus,
    AMLInvestigationCase,
    AMLMetricsResponse,
    AMLTransaction,
    CustomerRiskProfile,
    CustomerRiskTier,
    SARInvestigationDraft,
    TransactionDirection,
)
from aml.store import AMLStore

logger = logging.getLogger("finguard-aml-service")


class AMLService:
    """Service layer managing AML transaction monitoring and suspicious activity investigation."""

    def __init__(self, store: Optional[AMLStore] = None) -> None:
        self.store = store or AMLStore()

    def process_transaction(
        self, transaction: AMLTransaction
    ) -> Tuple[List[AMLAlert], Optional[AMLInvestigationCase], CustomerRiskProfile]:
        return self.store.process_transaction(transaction)

    def get_customer_profile(self, customer_id: str) -> Optional[CustomerRiskProfile]:
        return self.store.get_or_create_profile(customer_id)

    def list_cases(
        self,
        status: Optional[AMLCaseStatus] = None,
        risk_tier: Optional[CustomerRiskTier] = None,
        customer_id: Optional[str] = None,
    ) -> List[AMLInvestigationCase]:
        return self.store.list_cases(status=status, risk_tier=risk_tier, customer_id=customer_id)

    def get_case(self, case_id: str) -> Optional[AMLInvestigationCase]:
        return self.store.get_case(case_id)

    def update_case_status(
        self,
        case_id: str,
        new_status: AMLCaseStatus,
        actor: str = "aml.analyst",
        notes: Optional[str] = None,
    ) -> AMLInvestigationCase:
        return self.store.update_case_status(case_id, new_status, actor=actor, notes=notes)

    def add_case_note(
        self, case_id: str, author: str, content: str
    ) -> AMLInvestigationCase:
        return self.store.add_case_note(case_id, author, content)

    def generate_sar_draft(
        self,
        case_id: str,
        prepared_by: str = "aml.investigator",
        disposition: str = "RECOMMEND_SAR_FILING",
    ) -> SARInvestigationDraft:
        return self.store.generate_sar_draft(case_id, prepared_by, disposition)

    def get_metrics(self) -> AMLMetricsResponse:
        return self.store.get_metrics()

    def seed_demo_data(self) -> None:
        """Seed representative customer profiles and structured transaction patterns."""
        # Customer 1: Structuring Suspect
        p1 = self.store.get_or_create_profile(
            customer_id="CUST-AML-001",
            name="Robert Vance (Vance Global Holdings)",
            country="US",
            pep_flag=False,
        )
        self.process_transaction(
            AMLTransaction(
                transaction_id="TXN-STR-01",
                customer_id="CUST-AML-001",
                amount=9200.0,
                direction=TransactionDirection.OUTFLOW,
                payment_method="CASH_DEPOSIT",
            )
        )
        self.process_transaction(
            AMLTransaction(
                transaction_id="TXN-STR-02",
                customer_id="CUST-AML-001",
                amount=9400.0,
                direction=TransactionDirection.OUTFLOW,
                payment_method="CASH_DEPOSIT",
            )
        )

        # Customer 2: Large Cash / High Value
        self.store.get_or_create_profile(
            customer_id="CUST-AML-002",
            name="Elena Rostova (Consolidated Trade)",
            country="CY",
            pep_flag=True,
        )
        self.process_transaction(
            AMLTransaction(
                transaction_id="TXN-LARGE-01",
                customer_id="CUST-AML-002",
                amount=75000.0,
                direction=TransactionDirection.OUTFLOW,
                payment_method="CROSS_BORDER_WIRE",
            )
        )


# Global singleton instance
_GLOBAL_AML_SERVICE: Optional[AMLService] = None


def get_aml_service() -> AMLService:
    global _GLOBAL_AML_SERVICE
    if _GLOBAL_AML_SERVICE is None:
        _GLOBAL_AML_SERVICE = AMLService()
        _GLOBAL_AML_SERVICE.seed_demo_data()
    return _GLOBAL_AML_SERVICE

