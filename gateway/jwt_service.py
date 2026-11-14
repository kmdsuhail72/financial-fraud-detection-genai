"""
FinGuard AI — Phase 32: Enterprise JWT Authentication & Claims Service.
Generates and cryptographically validates JWT tokens using PyJWT with signature,
issuer, audience, and expiration verification.
"""
from __future__ import annotations

from datetime import timedelta
import os
import time
from typing import Any, Dict, List, Optional
import jwt

from gateway.models import AuthenticatedIdentity, GatewayRole

JWT_SECRET = os.getenv("GATEWAY_JWT_SECRET", "finguard-enterprise-gateway-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "https://auth.finguard.internal"
JWT_AUDIENCE = "finguard-api-gateway"


class JwtService:
    def __init__(
        self,
        secret: str = JWT_SECRET,
        issuer: str = JWT_ISSUER,
        audience: str = JWT_AUDIENCE,
        algorithm: str = JWT_ALGORITHM,
    ):
        self.secret = secret
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm

    def create_token(
        self,
        user_id: str,
        tenant_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        role: Optional[str] = None,
        expires_in_seconds: int = 3600,
        scopes: Optional[List[str]] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Encodes an RFC 7519 compliant JWT with issuer, audience, subject, and tenant claims."""
        now = int(time.time())
        exp = now + expires_in_seconds

        assigned_roles = []
        if roles:
            assigned_roles.extend(roles)
        if role and role not in assigned_roles:
            assigned_roles.append(role)
        if not assigned_roles:
            assigned_roles = [GatewayRole.ANALYST.value]

        payload = {
            "sub": user_id,
            "username": username or user_id,
            "email": email or f"{user_id}@finguard.internal",
            "tenant_id": tenant_id,
            "roles": assigned_roles,
            "role": assigned_roles[0],
            "scopes": scopes or ["cases:read"],
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "exp": exp,
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: Optional[str] = None,
        roles: Optional[List[str]] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
        expires_in_seconds: Optional[int] = None,
        scopes: Optional[List[str]] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convenience method for creating tokens with optional timedelta expiry."""
        sec = 3600
        if expires_delta is not None:
            sec = int(expires_delta.total_seconds())
        elif expires_in_seconds is not None:
            sec = expires_in_seconds

        return self.create_token(
            user_id=user_id,
            tenant_id=tenant_id,
            username=username,
            email=email,
            roles=roles,
            role=role,
            expires_in_seconds=sec,
            scopes=scopes,
            extra_claims=extra_claims,
        )

    def verify_token(self, token_str: str) -> AuthenticatedIdentity:
        """
        Cryptographically validates token signature, issuer, audience, and expiration.
        Raises jwt.PyJWTError subclasses on invalid tokens.
        """
        decoded = jwt.decode(
            token_str,
            self.secret,
            algorithms=[self.algorithm],
            issuer=self.issuer,
            audience=self.audience,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
                "require": ["exp", "iss", "aud", "sub", "tenant_id"],
            },
        )

        roles = decoded.get("roles", [])
        primary_role = decoded.get("role", roles[0] if roles else GatewayRole.ANALYST.value)
        if not roles and primary_role:
            roles = [primary_role]

        return AuthenticatedIdentity(
            user_id=decoded["sub"],
            username=decoded.get("username", decoded["sub"]),
            email=decoded.get("email", ""),
            roles=roles,
            role=primary_role,
            tenant_id=decoded["tenant_id"],
            scopes=decoded.get("scopes", []),
            token_issued_at=decoded.get("iat", 0),
            token_expires_at=decoded["exp"],
            raw_claims=decoded,
        )


# Global singleton service
jwt_service = JwtService()
