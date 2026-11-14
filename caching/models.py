"""
Phase 39: Enterprise Caching Architecture Models
Defines Pydantic models for caching policies, rate limiting, and idempotency.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CachePolicy(BaseModel):
    """Configuration for standard enterprise cache data policies."""
    data_type: str = Field(..., description="Category of data being cached")
    ttl_seconds: int = Field(..., description="Time to live in seconds")
    ttl_display: str = Field(..., description="Human readable TTL")
    invalidation_trigger: str = Field(..., description="Event that forces invalidation")
    description: str = Field(..., description="Usage guidelines")

    model_config = ConfigDict(extra="allow")


class CacheMetrics(BaseModel):
    """Real-time cache performance and access metrics."""
    hits: int = Field(default=0, description="Total cache hits")
    misses: int = Field(default=0, description="Total cache misses")
    hit_ratio: float = Field(default=0.0, description="Cache hit ratio (0.0 to 1.0)")
    evictions: int = Field(default=0, description="Eviction count")
    total_keys: int = Field(default=0, description="Current number of cached keys")
    backend_type: str = Field(default="memory", description="Active storage backend (memory | redis)")

    model_config = ConfigDict(extra="allow")


class RateLimitRequest(BaseModel):
    """Payload for checking distributed rate limit allocation."""
    identifier: str = Field(..., description="Unique client or tenant identifier")
    limit: int = Field(default=60, ge=1, description="Max requests permitted in window")
    window_seconds: int = Field(default=60, ge=1, description="Sliding/fixed window size in seconds")
    cost: int = Field(default=1, ge=1, description="Cost of the current request")

    model_config = ConfigDict(extra="allow")


class RateLimitResult(BaseModel):
    """Result of rate limit evaluation."""
    allowed: bool = Field(..., description="Whether the request is allowed through")
    current_count: int = Field(..., description="Total requests observed in current window")
    limit: int = Field(..., description="Configured ceiling")
    remaining: int = Field(..., description="Remaining quota in current window")
    reset_seconds: int = Field(..., description="Seconds until current window resets")
    retry_after: Optional[int] = Field(default=None, description="Seconds client must wait if throttled")

    model_config = ConfigDict(extra="allow")


class IdempotencyRequest(BaseModel):
    """Payload for verifying and registering an idempotent operation."""
    tenant_id: str = Field(..., description="Multi-tenant identifier")
    idempotency_key: str = Field(..., description="Client-supplied idempotency key")
    request_payload: Dict[str, Any] = Field(default_factory=dict, description="Request payload for verification")

    model_config = ConfigDict(extra="allow")


class IdempotencyRecord(BaseModel):
    """Stored record of an idempotent operation."""
    tenant_id: str = Field(..., description="Owning tenant")
    key_hash: str = Field(..., description="SHA-256 hash of tenant_id + idempotency_key")
    status: str = Field(default="COMPLETED", description="Execution status: IN_PROGRESS | COMPLETED")
    response_payload: Dict[str, Any] = Field(default_factory=dict, description="Cached response payload")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")
    is_replayed: bool = Field(default=False, description="Flag indicating if response was replayed from cache")

    model_config = ConfigDict(extra="allow")


class CustomerProfile(BaseModel):
    """Synthetic customer profile used in cache-aside testing."""
    customer_id: str
    name: str
    risk_tier: str
    country: str
    kyc_status: str
    email: str
    updated_at: str

    model_config = ConfigDict(extra="allow")


class ProfileUpdateRequest(BaseModel):
    """Request to update customer profile data, triggering cache invalidation."""
    name: Optional[str] = None
    risk_tier: Optional[str] = None
    country: Optional[str] = None
    kyc_status: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class CachingHealthResponse(BaseModel):
    """Health and status of the caching tier."""
    status: str
    backend: str
    redis_connected: bool
    metrics: CacheMetrics
    policies: List[CachePolicy]
    timestamp: str

    model_config = ConfigDict(extra="allow")
