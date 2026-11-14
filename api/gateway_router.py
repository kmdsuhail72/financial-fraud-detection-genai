"""
FinGuard AI — Phase 32: Enterprise API Gateway Router (/api/v1).
Versioned API Gateway routes featuring JWT authentication, RBAC, tenant isolation,
service credentials, and rate limiting.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from gateway.dependencies import (
    apply_rate_limit,
    get_authenticated_identity,
    require_role,
    require_service_auth,
)
from gateway.jwt_service import jwt_service
from gateway.models import (
    AuthenticatedIdentity,
    CreateTenantCaseRequest,
    GatewayMetrics,
    GatewayRole,
    ServiceEchoRequest,
    TenantCase,
    TokenCreateRequest,
    TokenResponse,
)
from gateway.rate_limiter import rate_limiter
from gateway.store import gateway_store

logger = logging.getLogger("finguard-gateway-api")

gateway_router = APIRouter(prefix="/api/v1", tags=["Enterprise API Gateway (v1)"])


def _extract_request_id(request: Request, response: Response) -> str:
    req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
    response.headers["X-Request-ID"] = req_id
    return req_id


@gateway_router.get("/health", summary="API Gateway v1 Health Check")
def gateway_health(request: Request, response: Response):
    """Returns the operational status of the Enterprise API Gateway (v1)."""
    req_id = _extract_request_id(request, response)
    gateway_store.record_request(is_authenticated=False)
    return {
        "status": "healthy",
        "service": "finguard-api-gateway",
        "version": "v1",
        "phase": "Phase-32",
        "features": [
            "jwt_authentication",
            "role_based_access_control",
            "multi_tenancy",
            "multi_tenancy_isolation",
            "service_to_service_auth",
            "rate_limiting",
            "sliding_window_rate_limiting",
            "distributed_request_tracing",
        ],
        "request_id": req_id,
    }


@gateway_router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Issue Synthetic JWT Access Token",
)
def generate_token(req: TokenCreateRequest, request: Request, response: Response) -> TokenResponse:
    """
    Generates a cryptographically signed JWT token with sub, roles, and tenant_id claims.
    """
    req_id = _extract_request_id(request, response)
    roles = req.roles or ([req.role] if req.role else [GatewayRole.ANALYST.value])
    primary_role = req.role or (roles[0] if roles else GatewayRole.ANALYST.value)

    token = jwt_service.create_token(
        user_id=req.user_id,
        tenant_id=req.tenant_id,
        username=req.username or req.user_id,
        email=req.email or f"{req.user_id}@finguard.internal",
        roles=roles,
        role=primary_role,
        expires_in_seconds=req.expires_in_seconds,
        scopes=req.scopes,
    )
    gateway_store.record_request(is_authenticated=False, tenant_id=req.tenant_id)

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=req.expires_in_seconds,
        tenant_id=req.tenant_id,
        roles=roles,
        role=primary_role,
    )


@gateway_router.get(
    "/auth/me",
    response_model=AuthenticatedIdentity,
    summary="Inspect Authenticated Identity & Claims",
)
def get_current_user_context(
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> AuthenticatedIdentity:
    """Returns decoded token context, active roles, and tenant boundaries."""
    _extract_request_id(request, response)
    return identity


@gateway_router.get(
    "/cases",
    response_model=List[TenantCase],
    summary="List Multi-Tenant Cases (Tenant Isolated)",
)
def list_tenant_cases(
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> List[TenantCase]:
    """
    Retrieves cases strictly scoped to caller's verified JWT tenant_id.
    Cross-tenant data exposure is mathematically prevented.
    """
    _extract_request_id(request, response)
    cases = gateway_store.list_tenant_cases(identity.tenant_id)
    return cases


@gateway_router.post(
    "/cases",
    response_model=TenantCase,
    status_code=status.HTTP_200_OK,
    summary="Create Tenant-Scoped Case",
)
def create_tenant_case(
    req: CreateTenantCaseRequest,
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> TenantCase:
    """Creates a new investigation case tagged with the caller's verified tenant_id."""
    _extract_request_id(request, response)
    case = gateway_store.create_tenant_case(
        tenant_id=identity.tenant_id,
        title=req.title,
        description=req.description,
        severity=req.severity,
        amount=req.amount,
    )
    return case


@gateway_router.post(
    "/service/echo",
    summary="Service-to-Service Machine Authentication Endpoint",
)
def service_to_service_echo(
    req: ServiceEchoRequest,
    request: Request,
    response: Response,
    service_account: str = Depends(require_service_auth),
):
    """
    Internal machine-to-machine endpoint protected by X-Service-Key credentials.
    Bypasses user JWT in favor of internal service trust.
    """
    req_id = _extract_request_id(request, response)
    return {
        "status": "acknowledged",
        "caller_type": "SERVICE_TO_SERVICE",
        "authenticated_service": req.service_name,
        "service_account": service_account,
        "received_action": req.action,
        "echo_payload": req.payload or {"message": req.message},
        "request_id": req_id,
    }


@gateway_router.get(
    "/admin/audit",
    summary="Admin & Auditor Privileged Route",
)
def admin_audit_dashboard(
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(
        require_role([GatewayRole.ADMIN.value, GatewayRole.AUDITOR.value, "admin", "auditor"])
    ),
):
    """
    Privileged operational route accessible strictly to Admin or Auditor roles.
    Unauthorized roles receive 403 Forbidden.
    """
    req_id = _extract_request_id(request, response)
    active_role = (identity.role or (identity.roles[0] if identity.roles else "admin")).lower()
    return {
        "status": "authorized",
        "authorized_role": active_role,
        "privileged_action": "SECURITY_AUDIT_INSPECTION",
        "caller": identity.username or identity.user_id,
        "roles": identity.roles,
        "tenant_id": identity.tenant_id,
        "audit_scope": "FULL_PLATFORM_READ",
        "request_id": req_id,
    }


@gateway_router.get(
    "/rate-limit-test",
    summary="Sliding-Window Rate Limit Tester",
)
def rate_limit_test(
    request: Request,
    response: Response,
):
    """
    Test endpoint enforcing a tight sliding-window limit (3 requests per 60 seconds).
    4th rapid call returns 429 Too Many Requests with Retry-After header.
    """
    req_id = _extract_request_id(request, response)
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"test-limiter:{client_ip}"

    allowed, remaining, retry_after = rate_limiter.is_allowed(key, limit=3, window_seconds=60)
    response.headers["X-RateLimit-Limit"] = "3"
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    if not allowed:
        gateway_store.record_request(is_rate_limited=True)
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded on test endpoint. Please back off.",
            headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
        )

    gateway_store.record_request(is_rate_limited=False)
    return {
        "status": "allowed",
        "remaining_requests": remaining,
        "window_seconds": 60,
        "request_id": req_id,
    }


@gateway_router.get(
    "/gateway/metrics",
    response_model=GatewayMetrics,
    summary="API Gateway Operational KPIs & Telemetry",
)
def get_gateway_metrics(request: Request, response: Response) -> GatewayMetrics:
    """Aggregates gateway throughput, authentication rates, S2S calls, and rate limit drops."""
    _extract_request_id(request, response)
    return gateway_store.get_metrics()
