"""Unit and Integration Tests for Phase 10 Authentication, RBAC, and Audit Logging."""

import os
import pytest
from fastapi.testclient import TestClient

from api.app import app
from security.auth import (
    AuthenticatedUser,
    CognitoJwtVerifier,
    TokenVerificationError,
    create_test_token,
)
from security.audit import audit_logger
from security.roles import Permission, Role, get_permissions_for_roles, has_permission


@pytest.fixture(autouse=True)
def clean_audit_logs():
    """Clear memory audit logs before each test."""
    audit_logger.clear()
    yield
    audit_logger.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ========================================================
# 1. RBAC Permissions Matrix Unit Tests
# ========================================================
def test_admin_has_all_permissions():
    """Verify Admin holds every permission in the matrix."""
    admin_perms = get_permissions_for_roles([Role.ADMIN.value])
    for perm in Permission:
        assert perm in admin_perms, f"Admin missing permission: {perm}"


def test_investigator_permissions():
    """Verify Investigator can view, assign, add notes, escalate, and resolve, but cannot view audit or manage users."""
    investigator_perms = get_permissions_for_roles([Role.INVESTIGATOR.value])
    assert Permission.VIEW_CASES in investigator_perms
    assert Permission.ASSIGN_CASES in investigator_perms
    assert Permission.ADD_NOTES in investigator_perms
    assert Permission.ESCALATE_CASES in investigator_perms
    assert Permission.RESOLVE_CASES in investigator_perms

    assert Permission.VIEW_AUDIT not in investigator_perms
    assert Permission.MANAGE_USERS not in investigator_perms


def test_analyst_permissions():
    """Verify Analyst can view, add notes, and escalate, but cannot assign, resolve, view audit, or manage users."""
    analyst_perms = get_permissions_for_roles([Role.ANALYST.value])
    assert Permission.VIEW_CASES in analyst_perms
    assert Permission.ADD_NOTES in analyst_perms
    assert Permission.ESCALATE_CASES in analyst_perms

    assert Permission.ASSIGN_CASES not in analyst_perms
    assert Permission.RESOLVE_CASES not in analyst_perms
    assert Permission.VIEW_AUDIT not in analyst_perms
    assert Permission.MANAGE_USERS not in analyst_perms


def test_auditor_permissions():
    """Verify Auditor can view cases and view audit history, but has zero write/mutation permissions."""
    auditor_perms = get_permissions_for_roles([Role.AUDITOR.value])
    assert Permission.VIEW_CASES in auditor_perms
    assert Permission.VIEW_AUDIT in auditor_perms

    assert Permission.ASSIGN_CASES not in auditor_perms
    assert Permission.ADD_NOTES not in auditor_perms
    assert Permission.ESCALATE_CASES not in auditor_perms
    assert Permission.RESOLVE_CASES not in auditor_perms
    assert Permission.MANAGE_USERS not in auditor_perms


# ========================================================
# 2. JWT Verification Unit Tests
# ========================================================
def test_valid_jwt_decoding():
    """Verify valid test token generates expected AuthenticatedUser context."""
    token = create_test_token(
        sub="usr-123",
        username="alex.mercer",
        email="alex@finguard.internal",
        roles=["Investigator"],
    )
    verifier = CognitoJwtVerifier(allow_mock=True)
    user = verifier.verify_token(token)

    assert user.sub == "usr-123"
    assert user.username == "alex.mercer"
    assert user.email == "alex@finguard.internal"
    assert "Investigator" in user.roles
    assert Permission.RESOLVE_CASES in user.permissions
    assert Permission.VIEW_AUDIT not in user.permissions


def test_expired_jwt_rejected():
    """Verify expired token raises TokenVerificationError."""
    token = create_test_token(expires_in_seconds=-10)
    verifier = CognitoJwtVerifier(allow_mock=True)
    with pytest.raises(TokenVerificationError) as exc_info:
        verifier.verify_token(token)
    assert "expired" in str(exc_info.value).lower() or "signature" in str(exc_info.value).lower()


def test_tampered_jwt_rejected():
    """Verify token signed with wrong secret is rejected."""
    token = create_test_token(mock_secret="wrong-secret-key-12345678901234567890")
    verifier = CognitoJwtVerifier(allow_mock=True, mock_secret="expected-secret-key-1234567890")
    with pytest.raises(TokenVerificationError):
        verifier.verify_token(token)


# ========================================================
# 3. Protected API Endpoints & RBAC Enforcement Tests
# ========================================================
def test_unauthenticated_request_rejected(client):
    """Calling protected endpoint without Authorization header must return 401."""
    resp = client.get("/cases")
    assert resp.status_code == 401
    assert "Authorization header" in resp.json()["detail"] or "Bearer" in resp.json()["detail"]


def test_invalid_token_request_rejected(client):
    """Calling protected endpoint with malformed/garbage token must return 401."""
    resp = client.get("/cases", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert resp.status_code == 401


def test_all_roles_can_view_cases(client):
    """Admin, Investigator, Analyst, and Auditor can all view /cases."""
    for role_name in ["Admin", "Investigator", "Analyst", "Auditor"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.get("/cases", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"Role {role_name} failed to view /cases: {resp.text}"


def test_assign_case_rbac_enforcement(client):
    """Only Admin and Investigator can assign cases. Analyst and Auditor must receive 403."""
    # Seed or get a case
    case_id = "CASE-123"

    # Permitted roles
    for role_name in ["Admin", "Investigator"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.post(
            f"/cases/{case_id}/assign",
            json={"assigned_to": "target_analyst@test.internal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Permitted role {role_name} failed: {resp.text}"

    # Forbidden roles
    for role_name in ["Analyst", "Auditor"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.post(
            f"/cases/{case_id}/assign",
            json={"assigned_to": "target_analyst@test.internal"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, f"Role {role_name} should have received 403, got {resp.status_code}"


def test_add_notes_rbac_enforcement(client):
    """Admin, Investigator, and Analyst can add notes. Auditor must receive 403."""
    case_id = "CASE-123"

    # Permitted roles
    for role_name in ["Admin", "Investigator", "Analyst"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.post(
            f"/cases/{case_id}/notes",
            json={"note": f"Observation logged by {role_name}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Role {role_name} failed to add note: {resp.text}"

    # Forbidden role: Auditor
    auditor_token = create_test_token(roles=["Auditor"], email="auditor@test.internal")
    resp = client.post(
        f"/cases/{case_id}/notes",
        json={"note": "Auditor unauthorized attempt"},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert resp.status_code == 403


def test_escalate_case_rbac_enforcement(client):
    """Admin, Investigator, and Analyst can escalate. Auditor must receive 403."""
    case_id = "CASE-123"

    # Permitted: Analyst
    analyst_token = create_test_token(roles=["Analyst"], email="analyst@test.internal")
    resp = client.post(
        f"/cases/{case_id}/escalate",
        json={"reason": "Velocity surge detected"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 200

    # Forbidden: Auditor
    auditor_token = create_test_token(roles=["Auditor"], email="auditor@test.internal")
    resp = client.post(
        f"/cases/{case_id}/escalate",
        json={"reason": "Auditor illegal attempt"},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert resp.status_code == 403


def test_resolve_case_rbac_enforcement(client):
    """Admin and Investigator can resolve. Analyst and Auditor must receive 403."""
    case_id = "CASE-123"

    # Permitted: Investigator
    inv_token = create_test_token(roles=["Investigator"], email="inv@test.internal")
    resp = client.post(
        f"/cases/{case_id}/resolve",
        json={"resolution_action": "CONFIRMED_FRAUD", "resolution_notes": "Card cancelled"},
        headers={"Authorization": f"Bearer {inv_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"

    # Forbidden: Analyst
    analyst_token = create_test_token(roles=["Analyst"], email="analyst@test.internal")
    resp = client.post(
        f"/cases/{case_id}/resolve",
        json={"resolution_action": "FALSE_POSITIVE"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403

    # Forbidden: Auditor
    auditor_token = create_test_token(roles=["Auditor"], email="auditor@test.internal")
    resp = client.post(
        f"/cases/{case_id}/resolve",
        json={"resolution_action": "CONFIRMED_FRAUD"},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert resp.status_code == 403


def test_audit_logs_access_rbac_enforcement(client):
    """Only Admin and Auditor can view audit logs. Investigator and Analyst must receive 403."""
    # Permitted: Admin and Auditor
    for role_name in ["Admin", "Auditor"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.get("/audit/logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"Role {role_name} failed to access audit logs: {resp.text}"

    # Forbidden: Investigator and Analyst
    for role_name in ["Investigator", "Analyst"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.get("/audit/logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, f"Role {role_name} should have received 403, got {resp.status_code}"


def test_manage_users_rbac_enforcement(client):
    """Only Admin can manage users and assign roles. All other roles receive 403."""
    admin_token = create_test_token(roles=["Admin"], email="admin@test.internal")
    resp = client.post(
        "/users/roles",
        json={"user_id": "usr-999", "role": "Investigator"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    for role_name in ["Investigator", "Analyst", "Auditor"]:
        token = create_test_token(roles=[role_name], email=f"{role_name.lower()}@test.internal")
        resp = client.post(
            "/users/roles",
            json={"user_id": "usr-999", "role": "Investigator"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


def test_tamper_evident_audit_log_generation(client):
    """Every authorized or denied action must automatically generate an audit log entry."""
    inv_token = create_test_token(roles=["Investigator"], email="inv@test.internal")
    client.post(
        "/cases/CASE-123/notes",
        json={"note": "Automated audit test note"},
        headers={"Authorization": f"Bearer {inv_token}"},
    )

    admin_token = create_test_token(roles=["Admin"], email="admin@test.internal")
    audit_resp = client.get("/audit/logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) > 0

    # Find the note action
    note_log = next((l for l in logs if l["action"] == "cases:notes:add"), None)
    assert note_log is not None
    assert note_log["actor_email"] == "inv@test.internal"
    assert note_log["resource_id"] == "CASE-123"
    assert note_log["status"] == "SUCCESS"

