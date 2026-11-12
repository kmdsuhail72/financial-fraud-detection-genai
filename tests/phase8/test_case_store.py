"""
Tests for CaseStore CRUD, Deduplication, and Audit Trail.
"""
import pytest
from investigation.case_store import CaseStore
from investigation.models import (
    CasePriority,
    CaseStatus,
    CaseUpdateRequest,
    InvestigationCase,
)


@pytest.fixture
def memory_case_store() -> CaseStore:
    return CaseStore(in_memory_fallback=True)


def test_create_and_deduplicate_case(memory_case_store):
    """Verify case creation and strict deduplication by transaction_id."""
    case1 = InvestigationCase(
        case_id="CASE-001",
        transaction_id="TXN-DEDUP-01",
        account_id="ACC-01",
        customer_id="CUS-01",
        amount=50000.0,
        risk_score=0.85,
        risk_level="HIGH",
    )

    # First insert succeeds
    assert memory_case_store.create_case(case1) is True

    # Duplicate transaction ID must be rejected
    case2 = InvestigationCase(
        case_id="CASE-002",
        transaction_id="TXN-DEDUP-01",
        account_id="ACC-01",
        customer_id="CUS-01",
        amount=50000.0,
        risk_score=0.85,
        risk_level="HIGH",
    )
    assert memory_case_store.create_case(case2) is False

    # Retrieve and verify
    fetched = memory_case_store.get_case("CASE-001")
    assert fetched is not None
    assert fetched.transaction_id == "TXN-DEDUP-01"
    assert len(fetched.audit_trail) >= 1
    assert fetched.audit_trail[0].action == "CASE_CREATED"


def test_update_case_notes_and_status(memory_case_store):
    """Verify analyst updates, notes, and audit trail entries."""
    case = InvestigationCase(
        case_id="CASE-003",
        transaction_id="TXN-UPDATE-01",
        account_id="ACC-03",
        customer_id="CUS-03",
        amount=75000.0,
        risk_score=0.75,
        risk_level="HIGH",
        status=CaseStatus.OPEN,
    )
    memory_case_store.create_case(case)

    # Apply update
    update_req = CaseUpdateRequest(
        status=CaseStatus.IN_REVIEW,
        assigned_to="analyst1@finguard.com",
        note="Customer contacted via registered phone.",
    )
    updated = memory_case_store.update_case("CASE-003", update_req, performed_by="analyst1@finguard.com")

    assert updated is not None
    assert updated.status == CaseStatus.IN_REVIEW
    assert updated.assigned_to == "analyst1@finguard.com"
    assert len(updated.notes) == 1
    assert updated.notes[0].content == "Customer contacted via registered phone."
    assert updated.notes[0].author == "analyst1@finguard.com"

    # Audit trail should record status change, assignment, and note addition
    actions = [entry.action for entry in updated.audit_trail]
    assert "STATUS_CHANGED" in actions
    assert "ANALYST_ASSIGNED" in actions
    assert "NOTE_ADDED" in actions
