"""
FinGuard AI — Phase 26: Identity Document Verification API Router
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from document_verification.models import (
    DocumentIntakeRequest,
    DocumentVerificationRecord,
    VerificationAssessmentRequest,
    TamperCheckRequest,
    DocumentAuditEvent,
)
from document_verification.service import get_verification_service

document_verification_router = APIRouter(prefix="/documents/verification", tags=["Identity Document Intelligence & Verification"])


@document_verification_router.get("/health")
def verification_health():
    """Health check for document verification and integrity service."""
    return {
        "status": "ok",
        "service": "document_verification",
        "version": "1.0.0"
    }


@document_verification_router.post("/intake", response_model=DocumentVerificationRecord, status_code=status.HTTP_201_CREATED)
def intake_document(req: DocumentIntakeRequest):
    """
    Ingests identity document (PDF, JPEG, PNG), computes SHA-256 integrity hash,
    and conducts field consistency checks against expected customer profile.
    """
    try:
        service = get_verification_service()
        return service.ingest_document(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@document_verification_router.get("/records", response_model=List[DocumentVerificationRecord])
def list_verification_records(
    customer_id: Optional[str] = Query(None, description="Filter records by customer ID")
):
    """Lists document verification records across the institution or for a specific customer."""
    service = get_verification_service()
    return service.store.list_records(customer_id=customer_id)


@document_verification_router.get("/records/{verification_id}", response_model=DocumentVerificationRecord)
def get_verification_record(verification_id: str):
    """Retrieves full document verification record by verification ID."""
    service = get_verification_service()
    record = service.store.get_record(verification_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Verification record '{verification_id}' not found")
    return record


@document_verification_router.post("/records/{verification_id}/tamper-check")
def check_document_tamper(verification_id: str, req: TamperCheckRequest):
    """
    Recalculates SHA-256 on modified/provided content and validates against
    the immutable recorded digest to detect tampering.
    """
    try:
        service = get_verification_service()
        return service.check_tamper(verification_id=verification_id, current_content=req.modified_content_raw)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@document_verification_router.post("/records/{verification_id}/assess", response_model=DocumentVerificationRecord)
def assess_verification_record(verification_id: str, req: VerificationAssessmentRequest):
    """Submits formal analyst verification decision (Verify, Flag Tamper, Reject Inconsistent)."""
    try:
        service = get_verification_service()
        return service.assess_verification(verification_id=verification_id, assessment_req=req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@document_verification_router.get("/customers/{customer_id}/timeline", response_model=List[DocumentVerificationRecord])
def get_customer_identity_timeline(customer_id: str):
    """Retrieves chronological identity document history for a customer."""
    service = get_verification_service()
    return service.get_customer_timeline(customer_id)


@document_verification_router.get("/customers/{customer_id}/audit-trail", response_model=List[DocumentAuditEvent])
def get_document_audit_trail(customer_id: str):
    """Retrieves chronological audit events for customer identity document actions."""
    service = get_verification_service()
    return service.get_audit_trail(customer_id)

