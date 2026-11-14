"""
FinGuard AI — Phase 30: Enterprise Regulatory Reporting (SAR/STR) Test Suite.
Validates:
1. Health check endpoint (/regulatory/health)
2. SAR/STR draft report creation with case/customer/evidence linking
3. Structural and duplicate reference validation
4. Review dispatch workflow (Draft -> Under Review)
5. Compliance review decision approval (Under Review -> Approved)
6. Rejection and return-to-draft workflows (Under Review -> Returned to Draft / Rejected)
7. Final regulatory submission and immutable audit trail verification
8. Reporting KPIs and statutory deadline monitoring
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app import app
from regulatory_reporting.models import ReportStatus, ReportType, ReviewDecision


@pytest.fixture
def client():
    return TestClient(app)


def test_regulatory_health_check(client):
    """1. Health check endpoint (/regulatory/health)."""
    resp = client.get("/regulatory/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "regulatory_reporting"
    assert data["phase"] == "Phase-30"
    assert "SAR" in data["templates"]
    assert "STR" in data["templates"]
    assert "FIU_IND" in data["jurisdictions"]


def test_create_sar_report_draft(client):
    """2. SAR report creation with case, customer, and evidence references."""
    fixture_path = Path("examples/report_create.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    resp = client.post("/reports", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["report_id"].startswith("SAR-")
    assert data["status"] == "DRAFT"
    assert data["customer_id"] == "CUST-BLR-40291"
    assert data["customer_name"] == "Jordan Cross"
    assert len(data["transaction_ids"]) == 3
    assert len(data["evidence_ids"]) == 2
    assert data["total_suspicious_amount"] == 1450000.0
    assert data["validation_result"]["is_valid"] is True


def test_report_validation_missing_fields_and_duplicates(client):
    """3. Validation checks detect missing narrative, empty transactions, and duplicates."""
    # Create invalid report with short narrative and duplicate transaction IDs
    invalid_payload = {
        "report_type": "STR",
        "jurisdiction": "FIU_IND",
        "customer_id": "CUST-INVALID-01",
        "customer_name": "Test Subject",
        "suspicion_narrative": "Too short",  # < 20 chars
        "primary_offense_category": "Structuring",
        "transaction_ids": ["TXN-DUP-01", "TXN-DUP-01"],  # Duplicate
        "evidence_ids": ["EV-01", "EV-01"],               # Duplicate
        "total_suspicious_amount": 0.0,                    # <= 0
    }
    create_resp = client.post("/reports", json=invalid_payload)
    assert create_resp.status_code == 201
    report_id = create_resp.json()["report_id"]

    val_resp = client.post(f"/reports/{report_id}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()

    assert val_data["is_valid"] is False
    fields_with_errors = [e["field"] for e in val_data["errors"]]
    assert "suspicion_narrative" in fields_with_errors
    assert "transaction_ids" in fields_with_errors
    assert "total_suspicious_amount" in fields_with_errors


def test_send_for_review_workflow(client):
    """4. Transition report from DRAFT to UNDER_REVIEW."""
    payload = {
        "report_type": "SAR",
        "customer_id": "CUST-REV-01",
        "customer_name": "Review Candidate",
        "suspicion_narrative": "Customer executed rapid transactions exceeding typical behavioral baseline.",
        "primary_offense_category": "Layering",
        "transaction_ids": ["TXN-REV-01"],
        "evidence_ids": ["EV-REV-01"],
        "total_suspicious_amount": 750000.0,
    }
    create_resp = client.post("/reports", json=payload)
    assert create_resp.status_code == 201
    report_id = create_resp.json()["report_id"]

    # Send for review
    send_resp = client.post(f"/reports/{report_id}/send-for-review")
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "UNDER_REVIEW"

    # Sending already under-review report should fail with 400
    send_again = client.post(f"/reports/{report_id}/send-for-review")
    assert send_again.status_code == 400


def test_review_approval_workflow(client):
    """5. Under review report can be approved by compliance reviewer."""
    payload = {
        "report_type": "STR",
        "customer_id": "CUST-APPROVE-01",
        "customer_name": "Approval Subject",
        "suspicion_narrative": "Transaction flow shows clear structuring below statutory reporting limit.",
        "primary_offense_category": "Structuring",
        "transaction_ids": ["TXN-APP-01"],
        "total_suspicious_amount": 950000.0,
    }
    create_resp = client.post("/reports", json=payload)
    report_id = create_resp.json()["report_id"]

    client.post(f"/reports/{report_id}/send-for-review")

    review_payload = {
        "decision": "APPROVE",
        "reviewer": "mlro@finguard.internal",
        "rationale": "Sufficient corroborating evidence. Approved for regulatory submission."
    }
    rev_resp = client.post(f"/reports/{report_id}/review", json=review_payload)
    assert rev_resp.status_code == 200
    data = rev_resp.json()
    assert data["status"] == "APPROVED"
    assert data["reviewed_by"] == "mlro@finguard.internal"
    assert "Approved" in data["review_notes"]


def test_rejection_and_return_to_draft_workflow(client):
    """6. Under review report can be rejected or returned to draft for corrections."""
    # Test return to draft
    p1 = {
        "report_type": "SAR",
        "customer_id": "CUST-RETURN-01",
        "customer_name": "Return Subject",
        "suspicion_narrative": "Initial suspicion of unusual activity across merchant terminals.",
        "primary_offense_category": "Merchant Fraud",
        "transaction_ids": ["TXN-RET-01"],
        "total_suspicious_amount": 400000.0,
    }
    r1 = client.post("/reports", json=p1).json()["report_id"]
    client.post(f"/reports/{r1}/send-for-review")

    ret_resp = client.post(
        f"/reports/{r1}/review",
        json={
            "decision": "RETURN_TO_DRAFT",
            "reviewer": "mlro@finguard.internal",
            "rationale": "Need additional statement evidence from sender bank."
        }
    )
    assert ret_resp.status_code == 200
    assert ret_resp.json()["status"] == "RETURNED_TO_DRAFT"

    # Test rejection
    p2 = {
        "report_type": "STR",
        "customer_id": "CUST-REJ-01",
        "customer_name": "Reject Subject",
        "suspicion_narrative": "Activity found to be legitimate business payroll after customer callback.",
        "primary_offense_category": "False Positive",
        "transaction_ids": ["TXN-REJ-01"],
        "total_suspicious_amount": 250000.0,
    }
    r2 = client.post("/reports", json=p2).json()["report_id"]
    client.post(f"/reports/{r2}/send-for-review")

    rej_resp = client.post(
        f"/reports/{r2}/review",
        json={
            "decision": "REJECT",
            "reviewer": "compliance_lead@finguard.internal",
            "rationale": "Commercial purpose verified. False positive confirmed."
        }
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "REJECTED"


def test_submission_tracking_and_audit_trail(client):
    """7. Regulatory submission tracking and full audit trail verification."""
    # Create, send for review, and approve report
    p = {
        "report_type": "SAR",
        "customer_id": "CUST-SUBMIT-01",
        "customer_name": "Submissible Entity",
        "suspicion_narrative": "Confirmed trade-based money laundering pattern across synthetic invoices.",
        "primary_offense_category": "Trade-Based Money Laundering",
        "transaction_ids": ["TXN-SUB-01", "TXN-SUB-02"],
        "evidence_ids": ["EV-INVOICE-01"],
        "total_suspicious_amount": 5000000.0,
    }
    rep_id = client.post("/reports", json=p).json()["report_id"]

    # Attempting to submit before approval must fail
    bad_submit = client.post(
        f"/reports/{rep_id}/submit",
        json={"external_filing_reference": "FIU-EARLY-01", "submitted_by": "officer@finguard.internal"}
    )
    assert bad_submit.status_code == 400

    # Review lifecycle: Draft -> Under Review -> Approved
    client.post(f"/reports/{rep_id}/send-for-review")
    client.post(
        f"/reports/{rep_id}/review",
        json={"decision": "APPROVE", "reviewer": "mlro@finguard.internal", "rationale": "Final approval granted."}
    )

    # Submit report
    submit_resp = client.post(
        f"/reports/{rep_id}/submit",
        json={
            "external_filing_reference": "FIU-IND-ACK-2026-FINAL-0099",
            "submitted_by": "mlro@finguard.internal",
            "submission_notes": "Filed via secure gateway API."
        }
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    assert sub_data["status"] == "SUBMITTED"
    assert sub_data["external_filing_reference"] == "FIU-IND-ACK-2026-FINAL-0099"
    assert sub_data["submitted_at"] is not None

    # Verify audit trail chronology
    audit_resp = client.get(f"/reports/{rep_id}/audit")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert len(events) >= 4
    actions = [e["action"] for e in events]
    assert "REPORT_CREATED" in actions
    assert "SENT_FOR_REVIEW" in actions
    assert "REPORT_APPROVED" in actions
    assert "REPORT_SUBMITTED" in actions


def test_metrics_and_deadline_monitoring(client):
    """8. Reporting metrics and statutory filing deadline aggregations."""
    resp = client.get("/reports/metrics")
    assert resp.status_code == 200
    metrics = resp.json()

    assert metrics["total_reports"] >= 2
    assert "draft_count" in metrics
    assert "under_review_count" in metrics
    assert "approved_count" in metrics
    assert "submitted_count" in metrics
    assert "rejected_count" in metrics
    assert "overdue_count" in metrics
    assert metrics["total_suspicious_amount_reported"] > 0

    # Also test /metrics alias
    alias_resp = client.get("/metrics")
    assert alias_resp.status_code == 200
    assert alias_resp.json()["total_reports"] == metrics["total_reports"]

