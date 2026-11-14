"""
FinGuard AI — Phase 32: Enterprise API Gateway & Security Models.
Defines schemas for JWT identities, tokens, tenant context, multi-tenant resources, and metrics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GatewayRole(str, Enum):
    ADMIN = "Admin"
    INVESTIGATOR = "Investigator"
    ANALYST = "Analyst"
    AUDITOR = "Auditor"


class AuthenticatedIdentity(BaseModel):
    user_id: str = Field(..., description="Subject identity (sub)")
    username: str = ""
    email: str = ""
    roles: List[str] = Field(default_factory=lambda: [GatewayRole.ANALYST.value])
    role: str = ""
    tenant_id: str = Field(..., description="Tenant organization partition key")
    is_service_account: bool = False
    scopes: List[str] = Field(default_factory=list)
    token_issued_at: int = 0
    token_expires_at: int = 0
    raw_claims: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class TokenCreateRequest(BaseModel):
    user_id: str = Field(default="usr-analyst-01")
    username: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    role: Optional[str] = None
    tenant_id: str = Field(default="tenant-alpha")
    expires_in_seconds: int = 3600
    scopes: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    tenant_id: str
    roles: List[str] = Field(default_factory=list)
    role: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class TenantCase(BaseModel):
    case_id: str
    tenant_id: str
    title: str
    severity: str = "HIGH"
    status: str = "OPEN"
    amount: float = 0.0
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class CreateTenantCaseRequest(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = "HIGH"
    amount: float = 0.0

    model_config = ConfigDict(extra="allow")


class ServiceEchoRequest(BaseModel):
    service_name: str
    action: str = "echo"
    message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class GatewayMetrics(BaseModel):
    total_requests: int
    authenticated_requests: int
    service_requests: int
    rate_limited_requests: int
    rate_limit_blocks: int = 0
    active_tenants_count: int
    tenant_traffic_distribution: Dict[str, int] = Field(default_factory=dict)
    avg_latency_ms: float

    model_config = ConfigDict(extra="allow")
