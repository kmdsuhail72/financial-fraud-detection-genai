"""
FinGuard AI — Phase 28: Customer Risk Assessment Store & History Registry
"""
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from customer_risk.models import (
    CustomerRiskAssessment,
    CustomerAssessmentRequest,
    CustomerRiskLevel,
    RiskDomain,
    DomainSignal,
    PreviousAssessmentComparison,
)
from customer_risk.engine import CustomerRiskEngine


class CustomerRiskStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._assessments: Dict[str, CustomerRiskAssessment] = {}  # assessment_id -> assessment
        self._customer_history: Dict[str, List[CustomerRiskAssessment]] = {}  # customer_id -> list
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Seed realistic demo profiles and the example assessment matching specification."""
        # 1. Prompt Example Profile: 39.0 / 100 — MEDIUM, 76% signal coverage across four domains
        # Domains: KYC (0.18), AML (0.22), FRAUD (0.20), IDENTITY (0.16) = sum 0.76 (76.0%)
        example_req = CustomerAssessmentRequest(
            customer_id="CUST-DEMO-39",
            customer_name="Jordan Cross",
            kyc_score=25.0,
            aml_score=45.0,
            fraud_score=40.0,
            identity_score=45.0,
            indicators={
                "KYC": ["Standard CDD completed; verified national ID."],
                "AML": ["Moderate cross-border remittance activity within expected corridor."],
                "FRAUD": ["Occasional off-hours mobile login attempts."],
                "IDENTITY": ["Single shared office address with registered affiliate."]
            },
            notes="Illustrative assessment matching Phase 28 benchmark."
        )
        assess_example = CustomerRiskEngine.calculate_assessment(example_req)
        self.save_assessment(assess_example)

        # 2. Clean Individual (Sarah Connor) - Low Risk across 7 domains
        sarah_req = CustomerAssessmentRequest(
            customer_id="CUST-US-9011",
            customer_name="Sarah Connor",
            kyc_score=10.0,
            aml_score=15.0,
            fraud_score=10.0,
            identity_score=5.0,
            sanctions_score=0.0,
            pep_score=0.0,
            behavioral_score=10.0,
            indicators={
                "KYC": ["Verified government passport with authentic SHA-256 integrity."],
                "IDENTITY": ["Zero attribute collisions; singular hardware device profile."]
            },
            notes="Baseline low-risk retail banking customer."
        )
        assess_sarah = CustomerRiskEngine.calculate_assessment(sarah_req)
        self.save_assessment(assess_sarah)

        # 3. Synthetic Fraud Ring Applicant (Alex Mercer) - Critical Risk
        alex_req = CustomerAssessmentRequest(
            customer_id="CUST-SYN-001",
            customer_name="Alex Mercer",
            kyc_score=75.0,
            aml_score=60.0,
            fraud_score=85.0,
            identity_score=95.0,
            sanctions_score=0.0,
            pep_score=0.0,
            behavioral_score=70.0,
            indicators={
                "IDENTITY": ["Identified in 3-applicant synthetic fraud ring sharing phone and device."],
                "FRAUD": ["High ML fraud probability (+85%) and velocity spike."],
                "KYC": ["EDD required due to document inconsistency."]
            },
            notes="Flagged by Phase 27 Identity Graph Intelligence."
        )
        assess_alex = CustomerRiskEngine.calculate_assessment(alex_req)
        self.save_assessment(assess_alex)

    def save_assessment(self, assessment: CustomerRiskAssessment) -> CustomerRiskAssessment:
        with self._lock:
            self._assessments[assessment.assessment_id] = assessment
            cid = assessment.customer_id
            if cid not in self._customer_history:
                self._customer_history[cid] = []
            self._customer_history[cid].append(assessment)
            return assessment

    def get_assessment(self, assessment_id: str) -> Optional[CustomerRiskAssessment]:
        with self._lock:
            return self._assessments.get(assessment_id)

    def get_latest_customer_assessment(self, customer_id: str) -> Optional[CustomerRiskAssessment]:
        with self._lock:
            history = self._customer_history.get(customer_id, [])
            return history[-1] if history else None

    def list_assessments(
        self,
        customer_id: Optional[str] = None,
        risk_level: Optional[CustomerRiskLevel] = None
    ) -> List[CustomerRiskAssessment]:
        with self._lock:
            results = list(self._assessments.values())
            if customer_id:
                results = [a for a in results if a.customer_id == customer_id]
            if risk_level:
                results = [a for a in results if a.risk_level == risk_level]
            return sorted(results, key=lambda a: a.assessed_at, reverse=True)

    def get_customer_history(self, customer_id: str) -> List[CustomerRiskAssessment]:
        with self._lock:
            return sorted(
                self._customer_history.get(customer_id, []),
                key=lambda a: a.assessed_at,
                reverse=True
            )


# Global singleton instance
_customer_risk_store = CustomerRiskStore()


def get_customer_risk_store() -> CustomerRiskStore:
    return _customer_risk_store
