"""
FinGuard AI — Phase 25: KYC Store & Audit Log Management
In-memory thread-safe customer registry with SHA-256 document verification and audit trail.
"""
import hashlib
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from kyc.models import (
    CustomerProfile,
    KYCDocument,
    CustomerAuditEvent,
    CustomerType,
    OnboardingStatus,
    DocumentType,
    DocumentStatus,
    RiskLevel,
    CDDTier,
    CustomerRiskAssessment,
)


def compute_sha256(content: str) -> str:
    """Computes SHA-256 hex digest for verification documents."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class KYCStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._customers: Dict[str, CustomerProfile] = {}
        self._audit_trail: Dict[str, List[CustomerAuditEvent]] = {}  # customer_id -> events
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Seed realistic demo profiles for testing and dashboard preview."""
        # 1. Clean Low Risk Individual
        c1_id = "CUST-US-9011"
        c1_doc = KYCDocument(
            document_id="DOC-9011-PASS",
            document_type=DocumentType.PASSPORT,
            issuing_country="US",
            document_number_masked="P*******42",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            uploaded_at=datetime.now(timezone.utc),
            status=DocumentStatus.VERIFIED
        )
        self._customers[c1_id] = CustomerProfile(
            customer_id=c1_id,
            customer_type=CustomerType.INDIVIDUAL,
            full_name="Sarah Connor",
            date_of_birth_or_inc="1984-05-12",
            nationality_or_country="US",
            email="sarah.c@techcorp-demo.com",
            phone="+1-555-0199",
            tax_id_masked="XXX-XX-4321",
            risk_assessment=CustomerRiskAssessment(
                risk_level=RiskLevel.LOW,
                score=10.0,
                risk_factors=["Verified government passport on file"],
                cdd_tier=CDDTier.SIMPLIFIED_SDD,
                explanation="LOW RISK: Clean screening history and verified passport."
            ),
            documents=[c1_doc],
            screening_matches=[],
            onboarding_status=OnboardingStatus.APPROVED,
            reviewed_by="analyst-system-auto",
            review_notes="Auto-approved standard low-risk onboarding."
        )
        self._log_audit_internal(
            customer_id=c1_id,
            event_type="CUSTOMER_ONBOARDED",
            actor="system",
            details={"action": "initial_seed"}
        )

        # 2. PEP Customer Requiring EDD
        c2_id = "CUST-GB-8840"
        c2_doc = KYCDocument(
            document_id="DOC-8840-ID",
            document_type=DocumentType.NATIONAL_ID,
            issuing_country="GB",
            document_number_masked="UK*******91",
            sha256_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            uploaded_at=datetime.now(timezone.utc),
            status=DocumentStatus.VERIFIED
        )
        self._customers[c2_id] = CustomerProfile(
            customer_id=c2_id,
            customer_type=CustomerType.INDIVIDUAL,
            full_name="Arthur Pendelton",
            date_of_birth_or_inc="1968-11-20",
            nationality_or_country="GB",
            email="arthur.pendelton@westminster-demo.gov",
            phone="+44-20-7946-0123",
            tax_id_masked="GB*******X",
            risk_assessment=CustomerRiskAssessment(
                risk_level=RiskLevel.HIGH,
                score=65.0,
                risk_factors=[
                    "Politically Exposed Person (PEP) match: 'Arthur Pendelton' (conf: HIGH)",
                    "Senior legislative official"
                ],
                cdd_tier=CDDTier.ENHANCED_EDD,
                explanation="HIGH RISK: PEP match detected. Enhanced Due Diligence (EDD) mandatory."
            ),
            documents=[c2_doc],
            screening_matches=[],
            onboarding_status=OnboardingStatus.EDD_REQUIRED,
            review_notes="Flagged for PEP review and source-of-wealth verification."
        )
        self._log_audit_internal(
            customer_id=c2_id,
            event_type="CUSTOMER_ONBOARDED",
            actor="system",
            details={"action": "initial_seed", "status": "EDD_REQUIRED"}
        )

        # 3. High Risk Entity with Sanctions Potential
        c3_id = "CUST-AE-4029"
        self._customers[c3_id] = CustomerProfile(
            customer_id=c3_id,
            customer_type=CustomerType.CORPORATE,
            full_name="Al-Farooq Logistics",
            date_of_birth_or_inc="2018-03-15",
            nationality_or_country="AE",
            email="compliance@alfarooq-demo.ae",
            phone="+971-4-123-4567",
            tax_id_masked="AE-TRN-****89",
            risk_assessment=CustomerRiskAssessment(
                risk_level=RiskLevel.CRITICAL,
                score=95.0,
                risk_factors=[
                    "Corporate Entity (requires beneficial ownership verification)",
                    "Sanctions Match detected: 'Al-Farooq Logistics' (conf: EXACT)",
                    "Offshore / Monitored Jurisdiction affiliation (AE)"
                ],
                cdd_tier=CDDTier.ENHANCED_EDD,
                explanation="CRITICAL RISK: Potential direct sanctions hit. Must undergo compliance review."
            ),
            documents=[],
            screening_matches=[],
            onboarding_status=OnboardingStatus.PENDING_REVIEW,
            review_notes="Pending compliance adjudication for sanctions match."
        )
        self._log_audit_internal(
            customer_id=c3_id,
            event_type="CUSTOMER_ONBOARDED",
            actor="system",
            details={"action": "initial_seed", "status": "PENDING_REVIEW"}
        )

    def _log_audit_internal(self, customer_id: str, event_type: str, actor: str, details: Dict):
        event = CustomerAuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            event_type=event_type,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
        if customer_id not in self._audit_trail:
            self._audit_trail[customer_id] = []
        self._audit_trail[customer_id].append(event)

    def save_customer(self, customer: CustomerProfile) -> CustomerProfile:
        with self._lock:
            self._customers[customer.customer_id] = customer
            return customer

    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        with self._lock:
            return self._customers.get(customer_id)

    def list_customers(
        self,
        status: Optional[OnboardingStatus] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> List[CustomerProfile]:
        with self._lock:
            results = list(self._customers.values())
            if status:
                results = [c for c in results if c.onboarding_status == status]
            if risk_level:
                results = [c for c in results if c.risk_assessment.risk_level == risk_level]
            return sorted(results, key=lambda c: c.updated_at, reverse=True)

    def log_audit(self, customer_id: str, event_type: str, actor: str, details: Dict) -> CustomerAuditEvent:
        with self._lock:
            event = CustomerAuditEvent(
                event_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                customer_id=customer_id,
                event_type=event_type,
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                details=details
            )
            if customer_id not in self._audit_trail:
                self._audit_trail[customer_id] = []
            self._audit_trail[customer_id].append(event)
            return event

    def get_audit_trail(self, customer_id: str) -> List[CustomerAuditEvent]:
        with self._lock:
            return sorted(
                self._audit_trail.get(customer_id, []),
                key=lambda e: e.timestamp,
                reverse=True
            )


# Global singleton instance
_kyc_store = KYCStore()


def get_kyc_store() -> KYCStore:
    return _kyc_store

