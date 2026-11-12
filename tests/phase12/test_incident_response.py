"""Unit and Integration Tests for Phase 12 Enterprise Incident Response & SOC Management."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from security.auth import create_test_token
from soc.ai_investigation import AIInvestigationAssistant
from soc.event_normalizer import EventNormalizer
from soc.incident_store import SOCIncidentStore
from soc.models import (
    ApprovalStatus,
    IncidentSeverity,
    IncidentStatus,
    NormalizedSecurityEvent,
)
from soc.playbooks import get_playbook_for_incident
from soc.remediation_executor import ControlledRemediationExecutor, RemediationExecutionError


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def clean_store():
    store = SOCIncidentStore()
    yield store
    store.clear()


# ========================================================
# 1. GuardDuty Event Normalization Test
# ========================================================
def test_event_normalization_guardduty():
    """Verify raw GuardDuty finding is correctly normalized into NormalizedSecurityEvent."""
    raw_gd = {
        "id": "gd-test-101",
        "detail": {
            "type": "UnauthorizedAccess:IAMUser/AnomalousBehavior",
            "title": "Anomalous API Invocation",
            "severity": 8.5,
            "resource": {
                "resourceType": "AWS::IAM::Role",
                "resourceId": "arn:aws:iam::123456789012:role/TestPaymentRole",
            },
        },
    }

    event = EventNormalizer.normalize(raw_gd)
    assert event.event_id == "gd-test-101"
    assert event.source == "GuardDuty"
    assert event.severity == IncidentSeverity.HIGH
    assert event.resource_id == "arn:aws:iam::123456789012:role/TestPaymentRole"
    assert event.fingerprint is not None
    assert len(event.fingerprint) == 16


# ========================================================
# 2. Security Hub & Fraud Alert Normalization Test
# ========================================================
def test_event_normalization_security_hub_and_fraud():
    """Verify Security Hub findings and FinGuard fraud alerts normalize properly."""
    raw_sh = {
        "source": "aws.securityhub",
        "Title": "S3 Public Read Access Detected",
        "severity": "CRITICAL",
        "resource_id": "arn:aws:s3:::sensitive-bucket",
    }
    event_sh = EventNormalizer.normalize(raw_sh)
    assert event_sh.source == "SecurityHub"
    assert event_sh.severity == IncidentSeverity.CRITICAL

    raw_fraud = {
        "source": "fraud-stream",
        "case_id": "CASE-999",
        "account_id": "ACC-55555",
        "risk_score": 0.92,
        "channel": "UPI",
    }
    event_fraud = EventNormalizer.normalize(raw_fraud)
    assert event_fraud.source == "FinGuardFraud"
    assert event_fraud.severity == IncidentSeverity.CRITICAL
    assert event_fraud.resource_id == "ACC-55555"


# ========================================================
# 3. Correlation & Deduplication Engine Test
# ========================================================
def test_event_deduplication_and_correlation(clean_store):
    """Verify related alerts on the same resource correlate into a single incident case."""
    event1 = NormalizedSecurityEvent(
        event_id="EVT-1",
        source="GuardDuty",
        event_type="IAMRoleAnomalousAccess",
        severity=IncidentSeverity.HIGH,
        resource_id="arn:aws:iam::123:role/AppRole",
        resource_type="AWS::IAM::Role",
        fingerprint="fp-iam-role-01",
    )

    incident_1 = clean_store.ingest_event(event1)
    assert incident_1.correlated_event_count == 1
    assert "EVT-1" in incident_1.correlated_event_ids

    # Second event on same resource
    event2 = NormalizedSecurityEvent(
        event_id="EVT-2",
        source="SecurityHub",
        event_type="PolicyPrivilegeEscalation",
        severity=IncidentSeverity.HIGH,
        resource_id="arn:aws:iam::123:role/AppRole",
        resource_type="AWS::IAM::Role",
        fingerprint="fp-iam-role-02",
    )

    incident_2 = clean_store.ingest_event(event2)
    # Must be correlated to the same incident case
    assert incident_2.incident_id == incident_1.incident_id
    assert incident_2.correlated_event_count == 2
    assert "EVT-2" in incident_2.correlated_event_ids


# ========================================================
# 4. Severity-Based SLA Target Calculation Test
# ========================================================
def test_sla_calculation(clean_store):
    """Verify SLA response targets match severity standards (Critical=15m, High=30m, etc.)."""
    crit_evt = NormalizedSecurityEvent(
        event_id="EVT-CRIT",
        source="GuardDuty",
        event_type="TrojanDetected",
        severity=IncidentSeverity.CRITICAL,
        resource_id="res-crit",
        resource_type="EC2",
        fingerprint="fp-crit",
    )
    inc_crit = clean_store.ingest_event(crit_evt)
    assert inc_crit.sla_target_minutes == 15

    high_evt = NormalizedSecurityEvent(
        event_id="EVT-HIGH",
        source="GuardDuty",
        event_type="SuspiciousAPI",
        severity=IncidentSeverity.HIGH,
        resource_id="res-high",
        resource_type="IAM",
        fingerprint="fp-high",
    )
    inc_high = clean_store.ingest_event(high_evt)
    assert inc_high.sla_target_minutes == 30


# ========================================================
# 5. AI Investigation Brief Synthesis Test
# ========================================================
def test_ai_investigation_brief_synthesis(clean_store):
    """Verify evidence brief produces hypotheses and recommended checks."""
    evt = NormalizedSecurityEvent(
        event_id="EVT-AI-TEST",
        source="GuardDuty",
        event_type="ExfiltrationS3",
        severity=IncidentSeverity.HIGH,
        resource_id="arn:aws:s3:::finguard-bronze",
        resource_type="AWS::S3::Bucket",
        fingerprint="fp-s3-exfil",
    )
    inc = clean_store.ingest_event(evt)
    assert inc.ai_brief is not None
    assert "GuardDuty" in inc.ai_brief.executive_summary
    assert len(inc.ai_brief.hypotheses) >= 3
    assert len(inc.ai_brief.recommended_checks) >= 3
    assert inc.ai_brief.confidence_score > 0.8


# ========================================================
# 6. Response Playbook Generation Test
# ========================================================
def test_playbook_generation():
    """Verify matching playbook is selected with dry-run plans and approval requirements."""
    pb = get_playbook_for_incident("AnomalousIAMBehavior", "arn:aws:iam:::role/AdminRole")
    assert pb.playbook_id == "PB-ACCOUNT-COMPROMISE"
    assert len(pb.actions) >= 1

    action = pb.actions[0]
    assert action.requires_approval is True
    assert "dry_run_plan" in action.model_dump()
    assert "rollback_guidance" in action.model_dump()


# ========================================================
# 7. Remediation Separation of Duties Approval Test
# ========================================================
def test_remediation_approval_separation_of_duties(clean_store):
    """Verify requester cannot approve their own action (separation of duties violation)."""
    evt = NormalizedSecurityEvent(
        event_id="EVT-SOD",
        source="GuardDuty",
        event_type="IAMCompromise",
        severity=IncidentSeverity.HIGH,
        resource_id="role-sod",
        resource_type="IAM",
        fingerprint="fp-sod",
    )
    inc = clean_store.ingest_event(evt)
    action_id = inc.playbooks[0].actions[0].action_id

    # Request approval by analyst
    analyst = "analyst@finguard.internal"
    approval = clean_store.request_approval(inc.incident_id, action_id, requested_by=analyst)

    # Attempt self-approval by same analyst
    clean_store.approve_action(
        inc.incident_id,
        approval.approval_id,
        approver=analyst,
        decision=ApprovalStatus.APPROVED,
    )

    # Execution must fail due to Separation of Duties
    with pytest.raises(Exception) as exc_info:
        clean_store.execute_remediation(inc.incident_id, action_id, executed_by=analyst)
    assert "separation of duties" in str(exc_info.value).lower() or "violation" in str(exc_info.value).lower()


# ========================================================
# 8. Controlled Remediation Execution & SOC API Test
# ========================================================
def test_controlled_remediation_execution_and_soc_api(client, clean_store):
    """Verify end-to-end execution with different approver updates status to CONTAINED and API functions."""
    evt = NormalizedSecurityEvent(
        event_id="EVT-EXEC-OK",
        source="GuardDuty",
        event_type="IAMCompromise",
        severity=IncidentSeverity.CRITICAL,
        resource_id="arn:aws:iam:::role/VictimRole",
        resource_type="IAM",
        fingerprint="fp-exec-ok",
    )
    inc = clean_store.ingest_event(evt)
    action_id = inc.playbooks[0].actions[0].action_id

    # 1. Request by Analyst
    appr = clean_store.request_approval(inc.incident_id, action_id, requested_by="analyst@finguard.internal")

    # 2. Approved by Separate Lead
    clean_store.approve_action(
        inc.incident_id,
        appr.approval_id,
        approver="soc-lead@finguard.internal",
        decision=ApprovalStatus.APPROVED,
        notes="Containment authorized.",
    )

    # 3. Execute
    receipt = clean_store.execute_remediation(
        inc.incident_id, action_id, executed_by="soc-lead@finguard.internal"
    )
    assert receipt.execution_status == "SIMULATED_SUCCESS"
    assert inc.status == IncidentStatus.CONTAINED

    # 4. Verify API
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    resp = client.get("/soc/incidents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    metrics_resp = client.get("/soc/metrics", headers={"Authorization": f"Bearer {token}"})
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "sla_compliance_percentage" in metrics

