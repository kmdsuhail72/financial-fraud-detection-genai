"""
FinGuard AI — Phase 23 Regulatory Compliance & Audit Governance Test Suite.
Validates:
1. Health check endpoint (HTTP 200)
2. Compliance catalogue initialization with 10 starter controls & framework mappings
3. Control assessment update with effectiveness status & rationale
4. Control effectiveness filtering (EFFECTIVE, PARTIALLY_EFFECTIVE, INEFFECTIVE)
5. Findings lifecycle management (Creation, ownership, severity, due dates)
6. Finding remediation workflow (Status transitions & remediation notes)
7. Audit trail logging of assessment & remediation events
8. Audit readiness snapshot & KPI calculation
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from governance.service import get_governance_service
from governance.models import ControlEffectiveness, FindingSeverity, RemediationStatus


@pytest.fixture(autouse=True)
def clean_governance_store():
    """Reset compliance catalogue and clear test state before each run."""
    service = get_governance_service()
    service.store.clear()
    yield
    service.store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_governance_health_endpoint(client):
    """1. Test health check on /compliance/governance/health."""
    resp = client.get("/compliance/governance/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert "Phase 23" in data["phase"]


def test_compliance_catalogue_initialization(client):
    """2. Test compliance catalogue initializes with exactly 10 starter controls and framework mappings."""
    resp = client.get("/compliance/governance/controls")
    assert resp.status_code == 200
    controls = resp.json()

    assert len(controls) == 10
    control_ids = [c["control_id"] for c in controls]
    assert "CTRL-IAM-01" in control_ids
    assert "CTRL-CRYPTO-02" in control_ids
    assert "CTRL-FRAUD-06" in control_ids
    assert "CTRL-FORENSICS-08" in control_ids

    # Verify framework mappings exist on controls
    for ctrl in controls:
        assert len(ctrl["framework_mappings"]) > 0
        frameworks = [m["framework"] for m in ctrl["framework_mappings"]]
        assert any(fw in ["SOC2", "ISO27001", "PCI_DSS", "FINCEN_AML"] for fw in frameworks)


def test_control_assessment_update(client):
    """3. Test updating control assessment with effectiveness, evidence refs, and rationale."""
    control_id = "CTRL-VULN-04"
    assessment_payload = {
        "effectiveness": "EFFECTIVE",
        "assessor_rationale": "Automated ECR container image scanning and Trivy pipeline checks successfully deployed.",
        "evidence_references": ["EVD-ECR-SCAN-VERIFIED", "EVD-TRIVY-REPORT"],
        "assessor": "senior.auditor@finguard.internal",
    }

    resp = client.post(f"/compliance/governance/controls/{control_id}/assess", json=assessment_payload)
    assert resp.status_code == 200
    updated = resp.json()

    assert updated["control_id"] == control_id
    assert updated["effectiveness"] == "EFFECTIVE"
    assert updated["assessed_by"] == "senior.auditor@finguard.internal"
    assert "EVD-ECR-SCAN-VERIFIED" in updated["evidence_references"]


def test_control_effectiveness_filtering(client):
    """4. Test query filtering of controls by effectiveness status."""
    resp_effective = client.get("/compliance/governance/controls?effectiveness=EFFECTIVE")
    assert resp_effective.status_code == 200
    effective_controls = resp_effective.json()
    assert len(effective_controls) >= 1
    for c in effective_controls:
        assert c["effectiveness"] == "EFFECTIVE"

    resp_partial = client.get("/compliance/governance/controls?effectiveness=PARTIALLY_EFFECTIVE")
    assert resp_partial.status_code == 200
    partial_controls = resp_partial.json()
    for c in partial_controls:
        assert c["effectiveness"] == "PARTIALLY_EFFECTIVE"


def test_findings_lifecycle_management(client):
    """5. Test creating and retrieving compliance findings linked to controls."""
    finding_payload = {
        "control_id": "CTRL-CRYPTO-02",
        "title": "KMS Key Rotation Verification Required",
        "description": "Annual cryptographic key rotation verification report missing for secondary region replica.",
        "severity": "HIGH",
        "owner": "security.infra@finguard.internal",
        "due_date": "2026-12-31",
    }

    create_resp = client.post("/compliance/governance/findings", json=finding_payload)
    assert create_resp.status_code == 201
    finding = create_resp.json()

    assert finding["finding_id"].startswith("FND-")
    assert finding["control_id"] == "CTRL-CRYPTO-02"
    assert finding["severity"] == "HIGH"
    assert finding["status"] == "OPEN"

    # List findings
    list_resp = client.get("/compliance/governance/findings?severity=HIGH")
    assert list_resp.status_code == 200
    findings = list_resp.json()
    assert any(f["finding_id"] == finding["finding_id"] for f in findings)


def test_finding_remediation_workflow(client):
    """6. Test transitioning finding remediation status and attaching notes."""
    # Create finding
    f_resp = client.post(
        "/compliance/governance/findings",
        json={
            "control_id": "CTRL-IAM-01",
            "title": "Inactive Admin Account Deprovisioning",
            "description": "Deprovision contractor admin credential after 60 days.",
            "severity": "MEDIUM",
            "owner": "iam.admin@finguard.internal",
            "due_date": "2026-11-30",
        },
    )
    finding_id = f_resp.json()["finding_id"]

    # Remediate finding
    remediate_payload = {
        "status": "REMEDIATED",
        "remediation_notes": "Contractor accounts audited and revoked via automated Cognito lifecycle job.",
        "remediated_by": "iam.admin@finguard.internal",
    }
    rem_resp = client.post(
        f"/compliance/governance/findings/{finding_id}/remediate", json=remediate_payload
    )
    assert rem_resp.status_code == 200
    updated_finding = rem_resp.json()

    assert updated_finding["status"] == "REMEDIATED"
    assert "Contractor accounts audited" in updated_finding["remediation_notes"]


def test_audit_trail_chronology(client):
    """7. Test audit trail records both control assessments and finding remediations."""
    # Assess control
    client.post(
        "/compliance/governance/controls/CTRL-NET-05/assess",
        json={"effectiveness": "EFFECTIVE", "assessor_rationale": "VPC endpoints verified."},
    )

    # Create & remediate finding
    f_resp = client.post(
        "/compliance/governance/findings",
        json={
            "control_id": "CTRL-NET-05",
            "title": "WAF Rate Limit Tuning",
            "description": "Tune rate limits for login API.",
            "severity": "LOW",
            "owner": "netops@finguard.internal",
            "due_date": "2026-12-01",
        },
    )
    f_id = f_resp.json()["finding_id"]
    client.post(
        f"/compliance/governance/findings/{f_id}/remediate",
        json={"status": "VERIFIED", "remediation_notes": "Rule updated to 500 req/5m."},
    )

    # Query audit trail
    audit_resp = client.get("/compliance/governance/audit-trail")
    assert audit_resp.status_code == 200
    trail = audit_resp.json()

    assert len(trail) >= 3
    event_types = [e["event_type"] for e in trail]
    assert "CONTROL_ASSESSED" in event_types
    assert "FINDING_CREATED" in event_types
    assert "FINDING_REMEDIATED" in event_types


def test_audit_readiness_snapshot_and_kpis(client):
    """8. Test calculation of overall audit-readiness percentage and framework breakdown."""
    resp = client.get("/compliance/governance/readiness")
    assert resp.status_code == 200
    readiness = resp.json()

    assert "overall_readiness_pct" in readiness
    assert readiness["overall_readiness_pct"] > 0.0
    assert readiness["total_controls"] == 10
    assert "SOC2" in readiness["framework_breakdown"]
    assert "ISO27001" in readiness["framework_breakdown"]
    assert "PCI_DSS" in readiness["framework_breakdown"]
    assert len(readiness["controls"]) == 10

