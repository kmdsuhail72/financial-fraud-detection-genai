"""
Tests for Investigation Case Domain Models.
"""
import pytest
from investigation.models import (
    AnalystNote,
    AuditTrailEntry,
    BedrockAISummary,
    CasePriority,
    CaseStatus,
    CaseUpdateRequest,
    InvestigationCase,
    ResolutionAction,
)


def test_investigation_case_initialization():
    """Verify default values and type validation on InvestigationCase."""
    case = InvestigationCase(
        case_id="CASE-20261112-0001",
        transaction_id="TXN-10001",
        account_id="ACC-20001",
        customer_id="CUS-30001",
        amount=125000.0,
        currency="INR",
        risk_score=0.88,
        risk_level="HIGH",
    )

    assert case.status == CaseStatus.OPEN
    assert case.priority == CasePriority.HIGH
    assert case.amount == 125000.0
    assert case.notes == []
    assert case.audit_trail == []
    assert case.created_at is not None


def test_case_update_request_validation():
    """Verify CaseUpdateRequest model parsing."""
    req = CaseUpdateRequest(
        status=CaseStatus.IN_REVIEW,
        assigned_to="lead.analyst@bank.com",
        note="Verifying recent mobile device bind logs.",
        resolution_action=ResolutionAction.CONFIRMED_FRAUD,
    )

    assert req.status == CaseStatus.IN_REVIEW
    assert req.assigned_to == "lead.analyst@bank.com"
    assert req.note == "Verifying recent mobile device bind logs."
    assert req.resolution_action == ResolutionAction.CONFIRMED_FRAUD

