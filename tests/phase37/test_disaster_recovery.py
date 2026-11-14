"""
FinGuard AI — Phase 37: Enterprise High Availability & Disaster Recovery Test Suite.
Validates:
1. DR subsystem health and multi-region readiness (/dr/health)
2. Approved RTO/RPO targets retrieval (/dr/targets)
3. Recovery assessment compliant scenario (/dr/assess)
4. Recovery assessment breach scenario (/dr/assess)
5. Failover planning when primary region is healthy (STAY_PRIMARY)
6. Failover proposal approval when secondary is ready & lag <= RPO (EXECUTE_FAILOVER)
7. Failover blocking when replication lag breaches RPO or secondary is unready
8. Backup manifest canonical SHA-256 integrity verification & tamper detection
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from disaster_recovery.backup import backup_manager
from disaster_recovery.models import FailoverAction, ServicePriority
from disaster_recovery.service import dr_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_dr_health_endpoint(client: TestClient):
    """1. Validates /dr/health reports active multi-region DR subsystem."""
    resp = client.get("/dr/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "READY"
    assert data["primary_region"] == "ap-south-1"
    assert data["secondary_region"] == "ap-southeast-1"
    assert data["s3_crr_active"] is True
    assert data["dynamodb_pitr_active"] is True
    assert data["targets_count"] >= 4


def test_get_rto_rpo_targets(client: TestClient):
    """2. Validates retrieval of approved RTO/RPO objectives for critical financial services."""
    resp = client.get("/dr/targets")
    assert resp.status_code == 200
    targets = resp.json()
    assert len(targets) >= 4

    target_map = {t["service_id"]: t for t in targets}

    # Transaction ingestion: RTO 30 min, RPO 5 min, P1
    txn = target_map["transaction-ingestion"]
    assert txn["target_rto_min"] == 30
    assert txn["target_rpo_min"] == 5
    assert txn["priority"] == "P1"

    # Fraud scoring: RTO 30 min, RPO 5 min, P1
    fraud = target_map["fraud-scoring"]
    assert fraud["target_rto_min"] == 30
    assert fraud["target_rpo_min"] == 5

    # Investigation API: RTO 60 min, RPO 15 min, P2
    inv = target_map["investigation-api"]
    assert inv["target_rto_min"] == 60
    assert inv["target_rpo_min"] == 15

    # Analytics lake: RTO 240 min, RPO 60 min, P4
    lake = target_map["analytics-lake"]
    assert lake["target_rto_min"] == 240
    assert lake["target_rpo_min"] == 60


def test_assess_recovery_compliant(client: TestClient):
    """3. Validates assessment evaluation when measured RTO & RPO are compliant."""
    payload = {
        "service_id": "transaction-ingestion",
        "measured_rto_min": 22.0,
        "measured_rpo_min": 3.0,
    }
    resp = client.post("/dr/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["service_id"] == "transaction-ingestion"
    assert data["rto_compliant"] is True
    assert data["rpo_compliant"] is True
    assert data["overall_compliant"] is True
    assert data["gap_rto_min"] == 0.0
    assert data["gap_rpo_min"] == 0.0
    assert data["status"] == "COMPLIANT"


def test_assess_recovery_breach(client: TestClient):
    """4. Validates assessment evaluation when measured values breach RTO/RPO limits."""
    payload = {
        "service_id": "transaction-ingestion",
        "measured_rto_min": 55.0,  # Target is 30m
        "measured_rpo_min": 12.0,  # Target is 5m
    }
    resp = client.post("/dr/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["rto_compliant"] is False
    assert data["rpo_compliant"] is False
    assert data["overall_compliant"] is False
    assert data["gap_rto_min"] == 25.0
    assert data["gap_rpo_min"] == 7.0
    assert data["status"] == "BREACHED"


def test_failover_plan_primary_healthy(client: TestClient):
    """5. Validates that failover is NOT recommended when the primary region is healthy."""
    payload = {
        "primary_healthy": True,
        "secondary_ready": True,
        "replication_lag_min": 1.0,
    }
    resp = client.post("/dr/failover/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["approved_for_failover"] is False
    assert data["recommended_action"] == "STAY_PRIMARY"
    assert "healthy and operational" in data["rationale"]


def test_failover_plan_secondary_ready_within_rpo(client: TestClient):
    """6. Validates that failover proposal is generated when primary is down, secondary is ready, and lag is within RPO."""
    payload = {
        "primary_healthy": False,
        "secondary_ready": True,
        "replication_lag_min": 2.5,  # <= 5 min RPO
        "authorized_by": "oncall-lead@finguard.ai",
    }
    resp = client.post("/dr/failover/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["approved_for_failover"] is True
    assert data["recommended_action"] == "EXECUTE_FAILOVER"
    assert data["human_approval_required"] is True
    assert data["authorized_by"] == "oncall-lead@finguard.ai"


def test_failover_plan_blocked_by_lag_or_readiness(client: TestClient):
    """7. Validates failover is blocked when replication lag exceeds RPO or secondary is not ready."""
    # Scenario A: Replication lag exceeds 5 minutes
    resp_lag = client.post(
        "/dr/failover/plan",
        json={"primary_healthy": False, "secondary_ready": True, "replication_lag_min": 9.5},
    )
    assert resp_lag.status_code == 200
    data_lag = resp_lag.json()
    assert data_lag["approved_for_failover"] is False
    assert data_lag["recommended_action"] == "BLOCKED_LAG_EXCEEDED"

    # Scenario B: Secondary warm standby is not ready
    resp_ready = client.post(
        "/dr/failover/plan",
        json={"primary_healthy": False, "secondary_ready": False, "replication_lag_min": 1.0},
    )
    assert resp_ready.status_code == 200
    data_ready = resp_ready.json()
    assert data_ready["approved_for_failover"] is False
    assert data_ready["recommended_action"] == "BLOCKED_SECONDARY_NOT_READY"


def test_backup_manifest_sha256_verification(client: TestClient):
    """8. Validates canonical SHA-256 verification and detection of corrupted/tampered backup files."""
    # Test authentic manifest
    resp_clean = client.post("/dr/backup/verify", json={"inject_corruption": False})
    assert resp_clean.status_code == 200
    data_clean = resp_clean.json()
    assert data_clean["valid"] is True
    assert data_clean["files_checked"] >= 3
    assert len(data_clean["mismatches"]) == 0

    # Test corrupted manifest
    resp_corrupt = client.post("/dr/backup/verify", json={"inject_corruption": True})
    assert resp_corrupt.status_code == 200
    data_corrupt = resp_corrupt.json()
    assert data_corrupt["valid"] is False
    assert len(data_corrupt["mismatches"]) > 0
    assert any("checksum" in m.lower() for m in data_corrupt["mismatches"])
