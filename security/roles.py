"""Role and Permission definitions for FinGuard AI RBAC."""

from enum import Enum
from typing import Dict, List, Set


class Role(str, Enum):
    """Cognito User Groups / Platform Roles."""
    ADMIN = "Admin"
    INVESTIGATOR = "Investigator"
    ANALYST = "Analyst"
    AUDITOR = "Auditor"


class Permission(str, Enum):
    """Granular action permissions enforced across API services."""
    VIEW_CASES = "cases:view"
    ASSIGN_CASES = "cases:assign"
    ADD_NOTES = "cases:notes:add"
    ESCALATE_CASES = "cases:escalate"
    RESOLVE_CASES = "cases:resolve"
    VIEW_AUDIT = "audit:view"
    MANAGE_USERS = "users:manage"


# RBAC Role-to-Permission mapping adhering strictly to the enterprise matrix
ROLE_PERMISSIONS_MAP: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.VIEW_CASES,
        Permission.ASSIGN_CASES,
        Permission.ADD_NOTES,
        Permission.ESCALATE_CASES,
        Permission.RESOLVE_CASES,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_USERS,
    },
    Role.INVESTIGATOR: {
        Permission.VIEW_CASES,
        Permission.ASSIGN_CASES,
        Permission.ADD_NOTES,
        Permission.ESCALATE_CASES,
        Permission.RESOLVE_CASES,
    },
    Role.ANALYST: {
        Permission.VIEW_CASES,
        Permission.ADD_NOTES,
        Permission.ESCALATE_CASES,
    },
    Role.AUDITOR: {
        Permission.VIEW_CASES,
        Permission.VIEW_AUDIT,
    },
}


def get_permissions_for_roles(roles: List[str]) -> Set[Permission]:
    """Resolve aggregate set of permissions from a list of assigned roles."""
    permissions: Set[Permission] = set()
    for role_str in roles:
        try:
            role = Role(role_str)
            permissions.update(ROLE_PERMISSIONS_MAP.get(role, set()))
        except ValueError:
            # Unrecognized role string, ignore safely
            continue
    return permissions


def has_permission(user_roles: List[str], required_permission: Permission) -> bool:
    """Check if the provided roles hold the required permission."""
    perms = get_permissions_for_roles(user_roles)
    return required_permission in perms

