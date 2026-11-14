"""
FinGuard AI — Phase 32: Enterprise API Gateway & Security.
"""
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
from gateway.jwt_service import JwtService, jwt_service
from gateway.rate_limiter import SlidingWindowRateLimiter, rate_limiter
from gateway.store import GatewayStore, gateway_store
from gateway.dependencies import (
    INTERNAL_SERVICE_KEY,
    apply_rate_limit,
    get_authenticated_identity,
    require_role,
    require_service_auth,
)

__all__ = [
    "AuthenticatedIdentity",
    "CreateTenantCaseRequest",
    "GatewayMetrics",
    "GatewayRole",
    "ServiceEchoRequest",
    "TenantCase",
    "TokenCreateRequest",
    "TokenResponse",
    "JwtService",
    "jwt_service",
    "SlidingWindowRateLimiter",
    "rate_limiter",
    "GatewayStore",
    "gateway_store",
    "INTERNAL_SERVICE_KEY",
    "apply_rate_limit",
    "get_authenticated_identity",
    "require_role",
    "require_service_auth",
]
