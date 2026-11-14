"""
FinGuard AI — Phase 32: Enterprise API Gateway, Microservices Security & Multi-Tenancy Test Suite.
Validates:
1. Gateway health and versioning (/api/v1/health)
2. JWT generation and authenticated identity validation (/api/v1/auth/token, /api/v1/auth/me)
3. JWT expiry, tampering, and signature validation
4. Role-based access control (RBAC) enforcement
5. Multi-tenant case isolation across tenants
6. Service-to-service (S2S) authentication (X-Service-Key)
7. Sliding-window rate limiting (429 Too Many Requests + Retry-After)
8. Request tracing (X-Request-ID) and gateway operational metrics (/api/v1/gateway/metrics)
"""
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from api.app import app
from gateway.jwt_service import jwt_service
from gateway.rate_limiter import rate_limiter
from gateway.store import gateway_store


@pytest.fixture
def client():
    # Reset in-memory rate limiter and metrics between test cycles if needed
    rate_limiter.reset()
    return TestClient(app)


def test_gateway_health(client):
    """1. Validates /api/v1/health, versioning, operational capabilities, and X-Request-ID."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "v1"
    assert data["service"] == "finguard-api-gateway"
    assert "jwt_authentication" in data["features"]
    assert "multi_tenancy" in data["features"]
    assert "rate_limiting" in data["features"]
    assert "X-Request-ID" in resp.headers


def test_jwt_token_generation_and_validation(client):
    """2. Validates token creation and decoding via /api/v1/auth/me."""
    token_payload = {
        "user_id": "analyst-001",
        "tenant_id": "tenant-alpha",
        "role": "analyst",
        "scopes": ["cases:read", "cases:write"],
    }
    resp = client.post("/api/v1/auth/token", json=token_payload)
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"].lower() == "bearer"
    assert token_data["tenant_id"] == "tenant-alpha"

    token = token_data["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    identity = me_resp.json()
    assert identity["user_id"] == "analyst-001"
    assert identity["tenant_id"] == "tenant-alpha"
    assert identity["role"] == "analyst"
    assert "cases:read" in identity["scopes"]


def test_jwt_expiry_and_invalid_signature(client):
    """3. Validates rejection of expired, forged, or missing JWTs (401 Unauthorized)."""
    # 1. Missing Authorization header
    resp_missing = client.get("/api/v1/auth/me")
    assert resp_missing.status_code == 401

    # 2. Expired token
    expired_token = jwt_service.create_access_token(
        user_id="usr-expired",
        tenant_id="tenant-alpha",
        role="analyst",
        expires_delta=timedelta(seconds=-60),
    )
    resp_expired = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401
    assert "expired" in resp_expired.json()["detail"].lower()

    # 3. Tampered token
    tampered_token = expired_token[:-4] + "fake"
    resp_tampered = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401


def test_role_based_access_control(client):
    """4. Validates RBAC: Analysts cannot access admin/audit routes; Admin and Auditor can."""
    # Analyst Token -> Expect 403 Forbidden on /api/v1/admin/audit
    analyst_token = jwt_service.create_access_token(
        user_id="usr-analyst",
        tenant_id="tenant-alpha",
        role="analyst",
    )
    resp_analyst = client.get(
        "/api/v1/admin/audit",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp_analyst.status_code == 403

    # Admin Token -> Expect 200 OK
    admin_token = jwt_service.create_access_token(
        user_id="usr-admin",
        tenant_id="tenant-alpha",
        role="admin",
    )
    resp_admin = client.get(
        "/api/v1/admin/audit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["authorized_role"] == "admin"

    # Auditor Token -> Expect 200 OK
    auditor_token = jwt_service.create_access_token(
        user_id="usr-auditor",
        tenant_id="tenant-beta",
        role="auditor",
    )
    resp_auditor = client.get(
        "/api/v1/admin/audit",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert resp_auditor.status_code == 200
    assert resp_auditor.json()["authorized_role"] == "auditor"


def test_multi_tenant_case_isolation(client):
    """5. Validates tenant data isolation: Tenant A cannot see Tenant B's cases."""
    alpha_token = jwt_service.create_access_token(
        user_id="alpha-agent",
        tenant_id="tenant-alpha",
        role="investigator",
    )
    beta_token = jwt_service.create_access_token(
        user_id="beta-agent",
        tenant_id="tenant-beta",
        role="investigator",
    )

    # 1. Create a distinct case under tenant-alpha
    create_resp = client.post(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {alpha_token}"},
        json={"title": "Confidential Alpha Fraud Case", "description": "High risk account takeover"},
    )
    assert create_resp.status_code == 200
    new_case = create_resp.json()
    new_case_id = new_case["case_id"]
    assert new_case["tenant_id"] == "tenant-alpha"

    # 2. Query cases with tenant-alpha token -> Must contain new_case_id and only tenant-alpha cases
    alpha_resp = client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {alpha_token}"},
    )
    assert alpha_resp.status_code == 200
    alpha_cases = alpha_resp.json()
    assert any(c["case_id"] == new_case_id for c in alpha_cases)
    for c in alpha_cases:
        assert c["tenant_id"] == "tenant-alpha"

    # 3. Query cases with tenant-beta token -> Must NOT contain new_case_id and only tenant-beta cases
    beta_resp = client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {beta_token}"},
    )
    assert beta_resp.status_code == 200
    beta_cases = beta_resp.json()
    assert not any(c["case_id"] == new_case_id for c in beta_cases)
    for c in beta_cases:
        assert c["tenant_id"] == "tenant-beta"


def test_service_to_service_authentication(client):
    """6. Validates machine-to-machine authentication via X-Service-Key."""
    payload = {"service_name": "scoring-pipeline", "message": "Sync batch inference job"}

    # 1. Valid service key -> 200 OK
    resp_valid = client.post(
        "/api/v1/service/echo",
        headers={"X-Service-Key": "finguard-internal-s2s-secret-key-2026"},
        json=payload,
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["status"] == "acknowledged"
    assert data["authenticated_service"] == "scoring-pipeline"

    # 2. Invalid service key -> 401 Unauthorized
    resp_invalid = client.post(
        "/api/v1/service/echo",
        headers={"X-Service-Key": "unauthorized-rogue-key"},
        json=payload,
    )
    assert resp_invalid.status_code == 401

    # 3. Missing service key -> 401 Unauthorized
    resp_missing = client.post(
        "/api/v1/service/echo",
        json=payload,
    )
    assert resp_missing.status_code == 401


def test_sliding_window_rate_limiting(client):
    """7. Validates sliding-window rate limiting returning 429 and Retry-After."""
    rate_limiter.reset()

    # /api/v1/rate-limit-test allows 3 requests per 60 seconds
    for i in range(3):
        resp = client.get("/api/v1/rate-limit-test")
        assert resp.status_code == 200
        assert resp.json()["status"] == "allowed"

    # 4th request must be throttled with HTTP 429
    resp_blocked = client.get("/api/v1/rate-limit-test")
    assert resp_blocked.status_code == 429
    assert "Retry-After" in resp_blocked.headers
    retry_after = int(resp_blocked.headers["Retry-After"])
    assert retry_after >= 1


def test_request_tracing_and_metrics(client):
    """8. Validates X-Request-ID propagation and operational metrics collection."""
    custom_trace_id = "trace-custom-correlation-uuid-999"
    resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_trace_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == custom_trace_id

    # Verify metrics aggregation
    metrics_resp = client.get("/api/v1/gateway/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_requests"] >= 1
    assert "tenant-alpha" in metrics["tenant_traffic_distribution"] or "unauthenticated" in metrics["tenant_traffic_distribution"]
    assert metrics["rate_limit_blocks"] >= 1
