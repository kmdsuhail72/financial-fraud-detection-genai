"""
FinGuard AI — Phase 25: KYC & Onboarding Orchestration Service
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from kyc.models import (
    CustomerProfile,
    CustomerOnboardingRequest,
    KYCDocument,
    DocumentUploadRequest,
    DocumentStatus,
    ComplianceReviewRequest,
    OnboardingStatus,
    RiskLevel,
    ReviewDecision,
    CustomerAuditEvent,
)
from kyc.store import KYCStore, get_kyc_store, compute_sha256
from kyc.screening import ScreeningEngine
from kyc.risk_engine import CustomerRiskEngine


class KYCService:
    def __init__(self, store: Optional[KYCStore] = None):
        self.store = store or get_kyc_store()
        self.screening_engine = ScreeningEngine(match_threshold=0.70)
        self.risk_engine = CustomerRiskEngine()

    def onboard_customer(self, req: CustomerOnboardingRequest, actor: str = "onboarding-service") -> CustomerProfile:
        # Check idempotency
        if req.customer_id:
            existing = self.store.get_customer(req.customer_id)
            if existing:
                return existing
            cid = req.customer_id
        else:
            cid = f"CUST-{req.nationality_or_country.upper()}-{uuid.uuid4().hex[:6].upper()}"

        documents = req.initial_documents or []
        
        # 1. Automatic Initial Screening
        screening_matches = self.screening_engine.screen(
            full_name=req.full_name,
            country=req.nationality_or_country
        )

        # 2. Risk Assessment
        risk_assessment = self.risk_engine.assess_risk(
            customer_type=req.customer_type,
            nationality_or_country=req.nationality_or_country,
            documents=documents,
            screening_matches=screening_matches
        )

        # 3. Determine Initial Status
        if risk_assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            initial_status = OnboardingStatus.EDD_REQUIRED
        else:
            initial_status = OnboardingStatus.PENDING_REVIEW

        profile = CustomerProfile(
            customer_id=cid,
            customer_type=req.customer_type,
            full_name=req.full_name,
            date_of_birth_or_inc=req.date_of_birth_or_inc,
            nationality_or_country=req.nationality_or_country,
            email=req.email,
            phone=req.phone,
            tax_id_masked=req.tax_id_masked,
            risk_assessment=risk_assessment,
            documents=documents,
            screening_matches=screening_matches,
            onboarding_status=initial_status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        self.store.save_customer(profile)
        self.store.log_audit(
            customer_id=cid,
            event_type="CUSTOMER_REGISTERED",
            actor=actor,
            details={
                "name": req.full_name,
                "country": req.nationality_or_country,
                "initial_risk_score": risk_assessment.score,
                "initial_status": initial_status.value,
                "matches_found": len(screening_matches)
            }
        )

        return profile

    def upload_document(
        self,
        customer_id: str,
        upload_req: DocumentUploadRequest,
        actor: str = "analyst"
    ) -> KYCDocument:
        customer = self.store.get_customer(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Compute or verify SHA-256
        if upload_req.provided_sha256:
            sha256_hash = upload_req.provided_sha256
        elif upload_req.content_raw:
            sha256_hash = compute_sha256(upload_req.content_raw)
        else:
            # Generate deterministic hash from doc number and type if raw content omitted
            sha256_hash = compute_sha256(f"{upload_req.document_type.value}:{upload_req.document_number_masked}:{customer_id}")

        doc = KYCDocument(
            document_id=f"DOC-{uuid.uuid4().hex[:8].upper()}",
            document_type=upload_req.document_type,
            issuing_country=upload_req.issuing_country,
            document_number_masked=upload_req.document_number_masked,
            sha256_hash=sha256_hash,
            uploaded_at=datetime.now(timezone.utc),
            status=DocumentStatus.VERIFIED,
            metadata=upload_req.metadata or {}
        )

        customer.documents.append(doc)
        
        # Re-assess risk with new document on file
        customer.risk_assessment = self.risk_engine.assess_risk(
            customer_type=customer.customer_type,
            nationality_or_country=customer.nationality_or_country,
            documents=customer.documents,
            screening_matches=customer.screening_matches
        )
        customer.updated_at = datetime.now(timezone.utc)
        self.store.save_customer(customer)

        self.store.log_audit(
            customer_id=customer_id,
            event_type="DOCUMENT_UPLOADED",
            actor=actor,
            details={
                "doc_id": doc.document_id,
                "type": doc.document_type.value,
                "sha256": doc.sha256_hash
            }
        )

        return doc

    def screen_customer(self, customer_id: str, actor: str = "analyst") -> List:
        customer = self.store.get_customer(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        matches = self.screening_engine.screen(
            full_name=customer.full_name,
            country=customer.nationality_or_country
        )
        customer.screening_matches = matches
        
        # Re-assess risk based on updated matches
        customer.risk_assessment = self.risk_engine.assess_risk(
            customer_type=customer.customer_type,
            nationality_or_country=customer.nationality_or_country,
            documents=customer.documents,
            screening_matches=matches
        )

        if customer.risk_assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            if customer.onboarding_status == OnboardingStatus.APPROVED:
                # Regress to EDD_REQUIRED if new high risks appear post-approval
                customer.onboarding_status = OnboardingStatus.EDD_REQUIRED
        
        customer.updated_at = datetime.now(timezone.utc)
        self.store.save_customer(customer)

        self.store.log_audit(
            customer_id=customer_id,
            event_type="SCREENING_PERFORMED",
            actor=actor,
            details={
                "matches_count": len(matches),
                "risk_score": customer.risk_assessment.score,
                "risk_level": customer.risk_assessment.risk_level.value
            }
        )

        return matches

    def review_customer(self, customer_id: str, review_req: ComplianceReviewRequest) -> CustomerProfile:
        customer = self.store.get_customer(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Map Decision to OnboardingStatus
        if review_req.decision == ReviewDecision.APPROVED:
            new_status = OnboardingStatus.APPROVED
        elif review_req.decision == ReviewDecision.REJECTED:
            new_status = OnboardingStatus.REJECTED
        elif review_req.decision == ReviewDecision.ESCALATED_EDD:
            new_status = OnboardingStatus.EDD_REQUIRED
        elif review_req.decision == ReviewDecision.REQUEST_INFO:
            new_status = OnboardingStatus.PENDING_REVIEW
        else:
            new_status = customer.onboarding_status

        customer.onboarding_status = new_status
        customer.reviewed_by = review_req.analyst_id
        customer.review_notes = review_req.rationale
        if review_req.edd_notes:
            customer.review_notes += f" | EDD Notes: {review_req.edd_notes}"
        customer.updated_at = datetime.now(timezone.utc)

        self.store.save_customer(customer)

        self.store.log_audit(
            customer_id=customer_id,
            event_type="COMPLIANCE_REVIEW_COMPLETED",
            actor=review_req.analyst_id,
            details={
                "decision": review_req.decision.value,
                "resulting_status": new_status.value,
                "rationale": review_req.rationale
            }
        )

        return customer

    def get_audit_trail(self, customer_id: str) -> List[CustomerAuditEvent]:
        return self.store.get_audit_trail(customer_id)


# Global singleton service
_kyc_service = KYCService()


def get_kyc_service() -> KYCService:
    return _kyc_service
