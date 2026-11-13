"""
FinGuard AI — Phase 25: KYC, CDD/EDD & Screening API Router
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from kyc.models import (
    CustomerProfile,
    CustomerOnboardingRequest,
    DocumentUploadRequest,
    KYCDocument,
    ComplianceReviewRequest,
    CustomerAuditEvent,
    ScreeningMatch,
    OnboardingStatus,
    RiskLevel,
)
from kyc.service import get_kyc_service

kyc_router = APIRouter(prefix="/kyc", tags=["Customer Onboarding & KYC"])


@kyc_router.get("/health")
def kyc_health():
    """Health check for KYC & Onboarding service."""
    return {
        "status": "ok",
        "service": "kyc_onboarding",
        "version": "1.0.0"
    }


@kyc_router.post("/customers", response_model=CustomerProfile, status_code=status.HTTP_201_CREATED)
def onboard_customer(req: CustomerOnboardingRequest):
    """
    Onboard a customer with automatic initial screening against synthetic PEP,
    Sanctions, and Adverse Media fixtures and CDD risk evaluation.
    """
    try:
        service = get_kyc_service()
        return service.onboard_customer(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@kyc_router.get("/customers", response_model=List[CustomerProfile])
def list_customers(
    status: Optional[OnboardingStatus] = Query(None, description="Filter by onboarding status"),
    risk_level: Optional[RiskLevel] = Query(None, description="Filter by evaluated risk level")
):
    """List onboarded customers with optional status or risk level filters."""
    service = get_kyc_service()
    return service.store.list_customers(status=status, risk_level=risk_level)


@kyc_router.get("/customers/{customer_id}", response_model=CustomerProfile)
def get_customer(customer_id: str):
    """Retrieve complete customer profile by ID."""
    service = get_kyc_service()
    customer = service.store.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    return customer


@kyc_router.post("/customers/{customer_id}/documents", response_model=KYCDocument, status_code=status.HTTP_201_CREATED)
def upload_kyc_document(customer_id: str, upload_req: DocumentUploadRequest):
    """Upload or register a KYC document with SHA-256 integrity verification."""
    try:
        service = get_kyc_service()
        return service.upload_document(customer_id=customer_id, upload_req=upload_req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@kyc_router.post("/customers/{customer_id}/screen", response_model=List[ScreeningMatch])
def screen_customer(customer_id: str):
    """Run comprehensive fuzzy-matching screening for PEP, Sanctions, and Adverse Media."""
    try:
        service = get_kyc_service()
        return service.screen_customer(customer_id=customer_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@kyc_router.post("/customers/{customer_id}/review", response_model=CustomerProfile)
def review_customer(customer_id: str, review_req: ComplianceReviewRequest):
    """Submit an analyst compliance decision (Approve, Reject, Escalate EDD) with formal rationale."""
    try:
        service = get_kyc_service()
        return service.review_customer(customer_id=customer_id, review_req=review_req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@kyc_router.get("/customers/{customer_id}/audit-trail", response_model=List[CustomerAuditEvent])
def get_customer_audit_trail(customer_id: str):
    """Fetch immutable chronological audit trail for a customer."""
    service = get_kyc_service()
    customer = service.store.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    return service.get_audit_trail(customer_id)

