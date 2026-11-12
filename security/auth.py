"""JWT Token Validation and Cognito Claims Verification."""

import os
import time
from typing import Any, Dict, List, Optional, Set
import urllib.request
import json
from pydantic import BaseModel, Field
from jose import jwt, JWTError

from security.roles import Permission, get_permissions_for_roles


class AuthenticatedUser(BaseModel):
    """Normalized security context extracted from verified JWT."""
    sub: str
    username: str
    email: str = ""
    roles: List[str] = Field(default_factory=list)
    permissions: Set[Permission] = Field(default_factory=set)
    token_use: str = "access"
    iss: str = ""
    exp: int = 0

    class Config:
        arbitrary_types_allowed = True


class TokenVerificationError(Exception):
    """Raised when token is malformed, expired, tampered, or invalid."""
    pass


class CognitoJwtVerifier:
    """Validates Amazon Cognito JWTs against the User Pool JWKS."""

    def __init__(
        self,
        region: Optional[str] = None,
        user_pool_id: Optional[str] = None,
        app_client_id: Optional[str] = None,
        allow_mock: Optional[bool] = None,
        mock_secret: Optional[str] = None,
    ):
        self.region = region or os.getenv("COGNITO_REGION", os.getenv("AWS_REGION", "ap-south-1"))
        self.user_pool_id = user_pool_id or os.getenv("COGNITO_USER_POOL_ID", "")
        self.app_client_id = app_client_id or os.getenv("COGNITO_APP_CLIENT_ID", "")
        self.allow_mock = (
            allow_mock
            if allow_mock is not None
            else os.getenv("AUTH_ALLOW_MOCK", "true").lower() == "true"
        )
        self.mock_secret = (
            mock_secret
            or os.getenv("AUTH_MOCK_SECRET", "finguard-insecure-mock-secret-for-dev-only")
        )
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0
        self._jwks_ttl: float = 3600  # 1 hour

    @property
    def expected_issuer(self) -> str:
        if not self.user_pool_id:
            return f"https://cognito-idp.{self.region}.amazonaws.com/ap-south-1_mock"
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    def fetch_jwks(self) -> Dict[str, Any]:
        """Fetch and cache JWKS from Cognito User Pool."""
        now = time.time()
        if self._jwks and (now - self._jwks_fetched_at < self._jwks_ttl):
            return self._jwks

        if not self.user_pool_id:
            return {"keys": []}

        jwks_url = f"{self.expected_issuer}/.well-known/jwks.json"
        try:
            req = urllib.request.Request(jwks_url, headers={"User-Agent": "FinGuard-AI-Auth"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                self._jwks = data
                self._jwks_fetched_at = now
                return data
        except Exception as e:
            # If network error or unreachable, fallback to cached if present
            if self._jwks:
                return self._jwks
            raise TokenVerificationError(f"Failed to fetch JWKS from {jwks_url}: {e}")

    def verify_token(self, token: str) -> AuthenticatedUser:
        """Decode and rigorously verify signature, issuer, expiration, and claims."""
        if not token:
            raise TokenVerificationError("Token is empty or missing")

        # Strip Bearer prefix if passed
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        # Check unverified header to determine key / alg
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise TokenVerificationError(f"Invalid token header: {e}")

        alg = unverified_header.get("alg")
        kid = unverified_header.get("kid")

        # 1. Mock / Test HS256 Token Handling
        if alg == "HS256":
            if not self.allow_mock:
                raise TokenVerificationError("HS256 symmetric tokens are disabled in production")
            try:
                payload = jwt.decode(
                    token,
                    self.mock_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
            except JWTError as e:
                raise TokenVerificationError(f"Mock token verification failed: {e}")

            return self._claims_to_user(payload)

        # 2. RS256 Cognito JWKS Token Handling
        if alg != "RS256":
            raise TokenVerificationError(f"Unsupported token algorithm: {alg}")

        jwks = self.fetch_jwks()
        keys = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), None)
        if not key:
            raise TokenVerificationError(f"Signing key '{kid}' not found in Cognito JWKS")

        try:
            # Verify signature, expiration, and issuer
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.expected_issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": False,  # Cognito access tokens use client_id claim instead of aud
                },
            )
        except JWTError as e:
            raise TokenVerificationError(f"Token validation failed: {e}")

        # Check client_id or aud if app_client_id is configured
        if self.app_client_id:
            client_id = payload.get("client_id") or payload.get("aud")
            if client_id != self.app_client_id:
                raise TokenVerificationError(
                    f"Token client_id '{client_id}' does not match expected '{self.app_client_id}'"
                )

        # Verify token_use
        token_use = payload.get("token_use")
        if token_use not in ("access", "id"):
            raise TokenVerificationError(f"Invalid token_use claim: '{token_use}'")

        return self._claims_to_user(payload)

    def _claims_to_user(self, payload: Dict[str, Any]) -> AuthenticatedUser:
        """Normalize Cognito token claims into AuthenticatedUser model."""
        sub = payload.get("sub", "")
        username = payload.get("cognito:username") or payload.get("username") or sub
        email = payload.get("email", "")

        # Extract Cognito groups (User Pool Groups)
        # In Cognito, groups are in the 'cognito:groups' array claim
        groups: List[str] = payload.get("cognito:groups") or payload.get("roles") or []
        if isinstance(groups, str):
            groups = [groups]

        permissions = get_permissions_for_roles(groups)

        return AuthenticatedUser(
            sub=sub,
            username=username,
            email=email,
            roles=groups,
            permissions=permissions,
            token_use=payload.get("token_use", "access"),
            iss=payload.get("iss", ""),
            exp=payload.get("exp", 0),
        )


def create_test_token(
    sub: str = "usr-test-001",
    username: str = "test.investigator",
    email: str = "investigator@finguard.internal",
    roles: Optional[List[str]] = None,
    expires_in_seconds: int = 3600,
    mock_secret: Optional[str] = None,
    issuer: Optional[str] = None,
) -> str:
    """Generate a signed mock JWT token for testing and local integration."""
    secret = mock_secret or os.getenv("AUTH_MOCK_SECRET", "finguard-insecure-mock-secret-for-dev-only")
    assigned_roles = roles if roles is not None else ["Investigator"]
    now = int(time.time())

    payload = {
        "sub": sub,
        "cognito:username": username,
        "username": username,
        "email": email,
        "cognito:groups": assigned_roles,
        "roles": assigned_roles,
        "token_use": "access",
        "iss": issuer or "https://cognito-idp.ap-south-1.amazonaws.com/test_pool",
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    return jwt.encode(payload, secret, algorithm="HS256")

