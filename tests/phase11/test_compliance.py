"""Unit and Integration Tests for Phase 11 Compliance & Risk Governance."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app import app
from compliance.control_mappings import get_default_control_mappings
from compliance.evidence_collector import EvidenceCollector
from compliance.models import (
    ComplianceFramework,
    CompliancePostureSummary,
    ComplianceReport,
    ControlMapping,
    ControlStatus,
    FindingSeverity,
    FindingStatus,
    SecurityFinding,
)
from security.auth import create_test_token
from security.roles import Role


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_snapshot_path():
    return "examples/sample_security_snapshot.json"


# ========================================================
# 1. Compliance Models Test
# ========================================================
def test_compliance_models_instantiation():
    """Verify models serialize and deserialize correctly."""
    finding = SecurityFinding(
        finding_id="FIND-TEST-1",
        title="Unencrypted S3 Bucket",
        description="Bucket lacks KMS SSE.",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        source="AWSConfig",
        resource_id="arn:aws:s3:::test-bucket",
        resource_type="AWS::S3::Bucket",
        remediation_steps=["Enable KMS CMK encryption."],
    )
    assert finding.finding_id == "FIND-TEST-1"
    assert finding.severity == FindingSeverity.HIGH
    assert finding.status == FindingStatus.OPEN

    dumped = finding.model_dump()
    assert dumped["severity"] == "HIGH"


# ========================================================
# 2. Control Mappings Inventory Test
# ========================================================
def test_default_control_mappings_inventory():
    """Verify default control inventory contains SOC 2 and ISO 27001 mappings."""
    controls = get_default_control_mappings()
    assert len(controls) == 10

    soc2_controls = [c for c in controls if c.framework == ComplianceFramework.SOC2]
    iso_controls = [c for c in controls if c.framework == ComplianceFramework.ISO27001]

    assert len(soc2_controls) == 5
    assert len(iso_controls) == 5

    soc2_ids = {c.control_id for c in soc2_controls}
    assert "SOC2-CC6.1" in soc2_ids
    assert "SOC2-CC7.2" in soc2_ids

    iso_ids = {c.control_id for c in iso_controls}
    assert "ISO-A.5.15" in iso_ids
    assert "ISO-A.8.24" in iso_ids


# ========================================================
# 3. Evidence Collector Snapshot Evaluation Test
# ========================================================
def test_evidence_collector_evaluates_snapshot(sample_snapshot_path):
    """Verify evidence collector parses snapshot and scores controls."""
    collector = EvidenceCollector(environment="test")
    snapshot = collector.load_snapshot(sample_snapshot_path)
    report = collector.collect_from_snapshot(snapshot)

    assert report.environment == "test"
    assert report.posture.total_controls == 10
    assert report.posture.compliant_controls == 10
    assert report.posture.non_compliant_controls == 0
    assert report.posture.compliance_percentage == 100.0

    # Verify frameworks breakdown
    assert report.posture.framework_scores["SOC2"] == 100.0
    assert report.posture.framework_scores["ISO27001"] == 100.0

    # Verify findings count
    assert len(report.findings) == 2
    assert report.posture.open_findings_count == 1
    assert report.posture.critical_findings_count == 0


# ========================================================
# 4. Non-Compliant Snapshot Evaluation Test
# ========================================================
def test_evidence_collector_non_compliant_evaluation():
    """Verify non-compliant telemetry marks appropriate controls NON_COMPLIANT."""
    bad_snapshot = {
        "cloudtrail": {
            "multi_region_enabled": False,
            "log_file_validation_enabled": False,
        },
        "kms": {
            "key_rotation_enabled": False,
        },
        "s3": {
            "all_buckets_encrypted": False,
            "block_public_access_enabled": False,
        },
        "cognito": {
            "mfa_configured": False,
        },
        "guardduty": {
            "detector_enabled": False,
        },
        "findings": [
            {
                "finding_id": "FIND-CRIT-01",
                "title": "Public S3 bucket detected",
                "severity": "CRITICAL",
                "status": "OPEN",
                "source": "GuardDuty",
            }
        ],
    }

    collector = EvidenceCollector(environment="dev")
    report = collector.collect_from_snapshot(bad_snapshot)

    assert report.posture.compliance_percentage < 100.0
    assert report.posture.non_compliant_controls >= 5
    assert report.posture.critical_findings_count == 1

    # Check specific controls
    ct_ctrl = next(c for c in report.controls if c.control_id == "SOC2-CC7.2")
    assert ct_ctrl.status == ControlStatus.NON_COMPLIANT

    kms_ctrl = next(c for c in report.controls if c.control_id == "ISO-A.8.24")
    assert kms_ctrl.status == ControlStatus.NON_COMPLIANT


# ========================================================
# 5. Compliance API Endpoints RBAC Test
# ========================================================
def test_compliance_api_endpoints_rbac(client):
    """Verify only Auditor and Admin can access compliance endpoints (Investigator and Analyst get 403)."""
    # 1. Permitted: Auditor
    auditor_token = create_test_token(roles=["Auditor"], email="auditor@finguard.internal")
    resp = client.get("/compliance/posture", headers={"Authorization": f"Bearer {auditor_token}"})
    assert resp.status_code == 200
    assert "compliance_percentage" in resp.json()

    controls_resp = client.get("/compliance/controls", headers={"Authorization": f"Bearer {auditor_token}"})
    assert controls_resp.status_code == 200
    assert len(controls_resp.json()) > 0

    findings_resp = client.get("/compliance/findings", headers={"Authorization": f"Bearer {auditor_token}"})
    assert findings_resp.status_code == 200

    # 2. Permitted: Admin
    admin_token = create_test_token(roles=["Admin"], email="admin@finguard.internal")
    post_resp = client.post("/compliance/evidence/collect", headers={"Authorization": f"Bearer {admin_token}"})
    assert post_resp.status_code == 201

    # 3. Forbidden: Analyst
    analyst_token = create_test_token(roles=["Analyst"], email="analyst@finguard.internal")
    denied_resp = client.get("/compliance/posture", headers={"Authorization": f"Bearer {analyst_token}"})
    assert denied_resp.status_code == 403

    # 4. Forbidden: Investigator
    inv_token = create_test_token(roles=["Investigator"], email="inv@finguard.internal")
    denied_inv = client.get("/compliance/posture", headers={"Authorization": f"Bearer {inv_token}"})
    assert denied_inv.status_code == 403

