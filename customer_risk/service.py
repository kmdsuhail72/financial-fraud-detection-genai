"""
FinGuard AI — Phase 28: Customer Risk Intelligence Orchestration Service
"""
from typing import List, Optional
from customer_risk.models import (
    CustomerRiskAssessment,
    CustomerAssessmentRequest,
    CustomerRiskLevel,
)
from customer_risk.store import CustomerRiskStore, get_customer_risk_store
from customer_risk.engine import CustomerRiskEngine


class CustomerRiskService:
    def __init__(self, store: Optional[CustomerRiskStore] = None):
        self.store = store or get_customer_risk_store()
        self.engine = CustomerRiskEngine()

    def assess_customer(self, req: CustomerAssessmentRequest) -> CustomerRiskAssessment:
        # Check previous assessment for continuous reassessment comparison
        previous = self.store.get_latest_customer_assessment(req.customer_id)
        
        # Calculate assessment with explainable multi-signal aggregation
        assessment = self.engine.calculate_assessment(req, previous_assessment=previous)
        
        # Persist assessment record
        self.store.save_assessment(assessment)
        return assessment

    def get_assessment(self, assessment_id: str) -> Optional[CustomerRiskAssessment]:
        return self.store.get_assessment(assessment_id)

    def list_assessments(
        self,
        customer_id: Optional[str] = None,
        risk_level: Optional[CustomerRiskLevel] = None
    ) -> List[CustomerRiskAssessment]:
        return self.store.list_assessments(customer_id=customer_id, risk_level=risk_level)

    def get_customer_history(self, customer_id: str) -> List[CustomerRiskAssessment]:
        return self.store.get_customer_history(customer_id)


# Global singleton service
_customer_risk_service = CustomerRiskService()


def get_customer_risk_service() -> CustomerRiskService:
    return _customer_risk_service

