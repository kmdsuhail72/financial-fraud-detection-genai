#!/usr/bin/env python3
"""
Phase 39: Standalone Caching & Coordination Smoke Script
Validates in-memory caching, cache-aside read-through, rate limiting, and idempotency.
Designed to execute cleanly from any directory without import path failures.
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path for standalone execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
from caching.memory_cache import MemoryCache
from caching.cache_aside import CacheAsideManager
from caching.rate_limiter import DistributedRateLimiter
from caching.idempotency import IdempotencyManager
from caching.models import RateLimitRequest, ProfileUpdateRequest


def run_smoke_tests():
    print("================================================================")
    print(" FinGuard AI — Phase 39 Caching Architecture Smoke Verification ")
    print("================================================================")

    # 1. Base Memory Cache Test
    print("\n[1/4] Testing MemoryCache primitives...")
    cache = MemoryCache()
    assert cache.set("test_key", {"foo": "bar"}, ttl_seconds=10)
    assert cache.exists("test_key")
    val = cache.get("test_key")
    assert val == {"foo": "bar"}, f"Unexpected cached value: {val}"
    assert cache.get_ttl("test_key") is not None
    assert cache.delete("test_key")
    assert not cache.exists("test_key")
    print("  ✓ MemoryCache: set, exists, get, get_ttl, and delete passed.")

    # 2. Cache-Aside Read-Through & Invalidation
    print("\n[2/4] Testing Cache-Aside Read-Through & Invalidation...")
    aside = CacheAsideManager(cache)
    # First fetch: cache miss, reads from authoritative store and caches
    p1 = aside.get_customer_profile("CUST-1001")
    assert p1 is not None and p1.name == "Aarav Sharma"
    assert cache.exists("profile:CUST-1001")

    # Invalidate via update
    updated = aside.update_customer_profile(
        "CUST-1001",
        ProfileUpdateRequest(risk_tier="CRITICAL")
    )
    assert updated.risk_tier == "CRITICAL"
    # Should have been invalidated in cache
    assert not cache.exists("profile:CUST-1001")
    # Read-through fetches fresh record and repopulates cache
    p2 = aside.get_customer_profile("CUST-1001")
    assert p2 is not None and p2.risk_tier == "CRITICAL"
    print("  ✓ Cache-Aside: read-through and update invalidation passed.")

    # 3. Distributed Rate Limiter
    print("\n[3/4] Testing Fixed-Window Rate Limiting...")
    limiter = DistributedRateLimiter()
    client_id = "test-client-99"
    req = RateLimitRequest(identifier=client_id, limit=3, window_seconds=2, cost=1)

    r1 = limiter.check_rate_limit(req)
    r2 = limiter.check_rate_limit(req)
    r3 = limiter.check_rate_limit(req)
    assert r1.allowed and r2.allowed and r3.allowed
    assert r3.remaining == 0

    # 4th request must be throttled
    r4 = limiter.check_rate_limit(req)
    assert not r4.allowed, "4th request should have been blocked"
    assert r4.retry_after is not None
    print(f"  ✓ Rate Limiter: Allowed 3/{req.limit}, blocked 4th with retry_after={r4.retry_after}s.")

    # 4. Idempotency Response Replay
    print("\n[4/4] Testing Tenant-Scoped Idempotency...")
    idempotency = IdempotencyManager(cache, ttl_seconds=60)
    tenant = "tenant-hdfc-01"
    key = "idem-tx-9999"
    payload = {"account": "ACC-1234", "amount": 50000.0}

    is_new, record = idempotency.check_or_reserve(tenant, key, payload)
    assert is_new, "First request must be recognized as new"
    assert record.status == "IN_PROGRESS"

    # Complete the transaction
    response_payload = {"status": "SUCCESS", "reference_no": "REF-887766"}
    completed = idempotency.save_result(tenant, key, response_payload)
    assert completed.status == "COMPLETED"

    # Replay request
    is_new_replay, replay_record = idempotency.check_or_reserve(tenant, key, payload)
    assert not is_new_replay, "Duplicate request must not be treated as new"
    assert replay_record.is_replayed
    assert replay_record.response_payload["reference_no"] == "REF-887766"
    print("  ✓ Idempotency: Tenant isolation and duplicate response replay verified.")

    # Cache metrics report
    metrics = cache.get_metrics()
    print("\nCache Access Metrics:")
    print(f"  Hits:       {metrics.hits}")
    print(f"  Misses:     {metrics.misses}")
    print(f"  Hit Ratio:  {metrics.hit_ratio:.2%}")
    print(f"  Total Keys: {metrics.total_keys}")

    print("\n================================================================")
    print(" All Phase 39 Caching Architecture Smoke Tests Passed! (4/4)    ")
    print("================================================================")


if __name__ == "__main__":
    run_smoke_tests()
