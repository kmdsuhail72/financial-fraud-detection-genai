"""
Phase 39: Enterprise Caching & Rate Limiting API Router
Mounted at /caching and /api/v1/caching
"""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, status
from caching.service import caching_service
from caching.models import (
    CachePolicy,
    CacheMetrics,
    RateLimitRequest,
    RateLimitResult,
    IdempotencyRequest,
    IdempotencyRecord,
    CustomerProfile,
    ProfileUpdateRequest,
    CachingHealthResponse,
)

router = APIRouter(prefix="/caching", tags=["Caching & Distributed Rate Limiting"])
caching_router = router


@router.get("/health", response_model=CachingHealthResponse)
def get_caching_health() -> CachingHealthResponse:
    """Return health status, metrics, and active backend of the caching layer."""
    return caching_service.get_health()


@router.get("/policies", response_model=List[CachePolicy])
def list_cache_policies() -> List[CachePolicy]:
    """List standard FinGuard cache TTL policies and invalidation rules."""
    return caching_service.get_policies()


@router.get("/metrics", response_model=CacheMetrics)
def get_cache_metrics() -> CacheMetrics:
    """Return real-time cache hits, misses, hit ratio, and memory key counts."""
    return caching_service.backend.get_metrics()


@router.get("/profile/{customer_id}", response_model=CustomerProfile)
def get_cached_customer_profile(customer_id: str) -> CustomerProfile:
    """Cache-aside read-through customer profile lookup."""
    profile = caching_service.cache_aside.get_customer_profile(customer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer profile '{customer_id}' not found in authoritative database",
        )
    return profile


@router.put("/profile/{customer_id}", response_model=CustomerProfile)
def update_customer_profile(customer_id: str, updates: ProfileUpdateRequest) -> CustomerProfile:
    """Update profile in authoritative DB and explicitly invalidate cache."""
    return caching_service.cache_aside.update_customer_profile(customer_id, updates)


@router.get("/merchant/{merchant_id}")
def get_cached_merchant_metadata(merchant_id: str) -> Dict[str, Any]:
    """Cache-aside merchant metadata lookup."""
    merchant = caching_service.cache_aside.get_merchant_metadata(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant metadata '{merchant_id}' not found",
        )
    return merchant


@router.post("/rate-limit/check", response_model=RateLimitResult)
def check_rate_limit(req: RateLimitRequest) -> RateLimitResult:
    """Evaluate distributed atomic rate limit."""
    res = caching_service.rate_limiter.check_rate_limit(req)
    if not res.allowed:
        # Return throttled response
        return res
    return res


@router.post("/idempotency/execute", response_model=IdempotencyRecord)
def execute_idempotent_operation(req: IdempotencyRequest) -> IdempotencyRecord:
    """
    Simulate an idempotent transaction or fraud score execution.
    Replays previous response if idempotency key matches for this tenant.
    """
    is_new, record = caching_service.idempotency.check_or_reserve(
        tenant_id=req.tenant_id,
        idempotency_key=req.idempotency_key,
        request_payload=req.request_payload,
    )

    if not is_new and record and record.status == "COMPLETED":
        # Replayed response
        return record

    # Perform mock business logic
    tx_id = req.request_payload.get("transaction_id", f"TX-{uuid.uuid4().hex[:8].upper()}")
    amount = req.request_payload.get("amount", 1000.0)
    decision = "APPROVED" if amount < 100000 else "FLAGGED_FOR_REVIEW"

    response_payload = {
        "transaction_id": tx_id,
        "amount": amount,
        "decision": decision,
        "risk_score": 0.12 if decision == "APPROVED" else 0.85,
        "processed_by": "FinGuard Fraud Engine v39",
    }

    # Save completed result to cache
    completed_record = caching_service.idempotency.save_result(
        tenant_id=req.tenant_id,
        idempotency_key=req.idempotency_key,
        response_payload=response_payload,
    )
    return completed_record


@router.post("/flush")
def flush_cache() -> Dict[str, Any]:
    """Evict all items from the active cache backend."""
    success = caching_service.backend.flush()
    return {"status": "flushed", "success": success}
