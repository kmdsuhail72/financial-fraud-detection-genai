"""FastAPI Security Dependencies for Authentication and RBAC."""

from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from security.auth import AuthenticatedUser, CognitoJwtVerifier, TokenVerificationError
from security.roles import Permission, Role, has_permission
from security.audit import audit_logger


# Default verifier instance
jwt_verifier = CognitoJwtVerifier()
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    """Validate Bearer JWT from Authorization header and return authenticated user."""
    if not credentials or not credentials.credentials:
        # Fallback check raw header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            audit_logger.log(
                actor_sub="anonymous",
                action="auth:missing_token",
                resource_type="API",
                resource_id=request.url.path,
                status="DENIED",
                ip_address=request.client.host if request.client else None,
                details={"path": request.url.path, "method": request.method},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or malformed Authorization header. Bearer token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth_header[7:].strip()
    else:
        token = credentials.credentials

    try:
        user = jwt_verifier.verify_token(token)
        return user
    except TokenVerificationError as e:
        audit_logger.log(
            actor_sub="unverified",
            action="auth:invalid_token",
            resource_type="API",
            resource_id=request.url.path,
            status="DENIED",
            ip_address=request.client.host if request.client else None,
            details={"error": str(e), "path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(required_permission: Permission) -> Callable:
    """Dependency factory ensuring user has the required permission."""

    def _permission_dependency(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if required_permission not in current_user.permissions:
            audit_logger.log(
                actor_sub=current_user.sub,
                actor_email=current_user.email,
                actor_roles=current_user.roles,
                action=f"rbac:denied:{required_permission.value}",
                resource_type="API",
                resource_id=request.url.path,
                status="DENIED",
                ip_address=request.client.host if request.client else None,
                details={
                    "required_permission": required_permission.value,
                    "user_roles": current_user.roles,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required permission: '{required_permission.value}'",
            )
        return current_user

    return _permission_dependency


def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency factory ensuring user holds at least one of the specified roles."""

    def _role_dependency(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        user_roles_set = set(current_user.roles)
        allowed_set = {r if isinstance(r, str) else r.value for r in allowed_roles}
        if not (user_roles_set & allowed_set):
            audit_logger.log(
                actor_sub=current_user.sub,
                actor_email=current_user.email,
                actor_roles=current_user.roles,
                action="rbac:role_denied",
                resource_type="API",
                resource_id=request.url.path,
                status="DENIED",
                ip_address=request.client.host if request.client else None,
                details={
                    "allowed_roles": list(allowed_set),
                    "user_roles": current_user.roles,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: User must belong to one of roles: {list(allowed_set)}",
            )
        return current_user

    return _role_dependency

