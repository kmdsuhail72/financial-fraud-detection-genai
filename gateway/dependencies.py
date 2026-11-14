"""
FinGuard AI — Phase 32: FastAPI Security & RBAC Dependencies.
Enforces JWT authentication, role-based authorization, tenant isolation, and service keys.
"""
from __future__ import annotations

import os
import time
from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
import jwt

from gateway.jwt_service import jwt_service
from gateway.models import AuthenticatedIdentity, GatewayRole
from gateway.rate_limiter import rate_limiter
from gateway.store import gateway_store

INTERNAL_SERVICE_KEY = os.getenv("GATEWAY_SERVICE_KEY", "finguard-internal-s2s-secret-key-2026")


def get_authenticated_identity(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedIdentity:
    """
    Validates JWT Bearer token from Authorization header and extracts tenant/user context.
    """
    if not authorization:
        gateway_store.record_request(is_authenticated=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        gateway_store.record_request(is_authenticated=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        identity = jwt_service.verify_token(token)
        # Store context in request state for downstream handlers
        request.state.identity = identity
        request.state.tenant_id = identity.tenant_id
        gateway_store.record_request(is_authenticated=True)
        return identity
    except jwt.ExpiredSignatureError:
        gateway_store.record_request(is_authenticated=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token has expired.",
            headers={"WWW-Authenticate": "Bearer error='invalid_token', error_description='Token expired'"},
        )
    except jwt.PyJWTError as exc:
        gateway_store.record_request(is_authenticated=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT verification error: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer error='invalid_token'"},
        )


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Factory dependency enforcing that the caller possesses at least one of the permitted roles.
    """
    def role_checker(identity: AuthenticatedIdentity = Depends(get_authenticated_identity)) -> AuthenticatedIdentity:
        # Case-insensitive role comparison
        allowed_upper = [r.upper() for r in allowed_roles]
        user_roles_upper = [r.upper() for r in identity.roles]

        has_access = any(r in allowed_upper for r in user_roles_upper)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User roles {identity.roles} lack required permissions ({allowed_roles}).",
            )
        return identity

    return role_checker


def require_service_auth(
    x_service_key: Optional[str] = Header(None, alias="X-Service-Key"),
) -> str:
    """
    Validates machine-to-machine internal service credentials.
    """
    if not x_service_key or x_service_key != INTERNAL_SERVICE_KEY:
        gateway_store.record_request(is_service=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Service-Key credential.",
        )

    gateway_store.record_request(is_service=True)
    return "internal-service-account"


def apply_rate_limit(
    request: Request,
    limit: int = 60,
    window_seconds: int = 60,
):
    """
    Dependency enforcing sliding-window rate limit on caller IP or tenant.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    tenant = getattr(request.state, "tenant_id", "anonymous")
    rate_key = f"{client_ip}:{tenant}"

    allowed, remaining, retry_after = rate_limiter.is_allowed(
        rate_key, limit=limit, window_seconds=window_seconds
    )
    if not allowed:
        gateway_store.record_request(is_rate_limited=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many requests.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
