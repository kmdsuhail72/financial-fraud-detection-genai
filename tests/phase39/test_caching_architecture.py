"""
FinGuard AI — Phase 39 Test Suite: Enterprise Caching Architecture & Distributed Rate Limiting
Verifies:
1. Memory cache CRUD operations and TTL expiry
2. Cache-aside read-through and customer profile invalidation
3. Redis cache adapter mock & JSON serialization
4. Fixed-window rate limiting (allowed quota vs throttling)
5. Atomic Redis Lua rate limiting script structure
6. Tenant-scoped idempotency key hashing and replay
7. Caching service health, metrics, and policy registry
8. Terraform ElastiCache and Docker Compose configuration validation
"""

import os
import time
from unittest.mock import MagicMock
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import app
from caching.memory_cache import MemoryCache
from caching.redis_cache import RedisCache
from caching.cache_aside import CacheAsideManager
from caching.rate_limiter import DistributedRateLimiter, REDIS_LUA_RATE_LIMITER
from caching.idempotency import IdempotencyManager
from caching.service import caching_service
from caching.models import RateLimitRequest, ProfileUpdateRequest


client = TestClient(app)


def test_memory_cache_crud_and_ttl_expiry():
    """1. Test in-memory cache operations, key existence, deletion, and TTL expiration."""
    cache = MemoryCache(max_keys=100)
    key = "session:test-user-1"
    payload = {"user_id": "U-1234", "role": "ANALYST"}

    # Set with short TTL
    assert cache.set(key, payload, ttl_seconds=1)
    assert cache.exists(key)
    cached = cache.get(key)
    assert cached == payload
    assert cache.get_ttl(key) is not None

    # Wait for TTL expiry
    time.sleep(1.1)
    assert cache.get(key) is None
    assert not cache.exists(key)
    assert cache.get_ttl(key) is None

    # Test deletion and flush
    cache.set("key1", "val1")
    cache.set("key2", "val2")
    assert cache.delete("key1")
    assert not cache.exists("key1")
    assert cache.flush()
    assert cache.get_metrics().total_keys == 0


def test_cache_aside_read_through_and_profile_invalidation():
    """2. Test cache-aside read-through fetching and profile update cache invalidation."""
    cache = MemoryCache()
    manager = CacheAsideManager(cache)
    cust_id = "CUST-1002"

    # Initial state: not cached
    assert not cache.exists(f"profile:{cust_id}")

    # Read-through: cache miss -> authoritative DB -> cached
    p1 = manager.get_customer_profile(cust_id)
    assert p1 is not None
    assert p1.name == "Priya Patel"
    assert cache.exists(f"profile:{cust_id}")

    # Second read: cache hit
    p1_cached = manager.get_customer_profile(cust_id)
    assert p1_cached.name == "Priya Patel"

    # Update profile in authoritative DB -> cache is invalidated
    updated = manager.update_customer_profile(
        cust_id,
        ProfileUpdateRequest(risk_tier="CRITICAL", country="IN")
    )
    assert updated.risk_tier == "CRITICAL"
    assert not cache.exists(f"profile:{cust_id}")

    # Next read fetches freshly updated record and caches it
    p2 = manager.get_customer_profile(cust_id)
    assert p2 is not None
    assert p2.risk_tier == "CRITICAL"
    assert cache.exists(f"profile:{cust_id}")


def test_redis_cache_adapter_and_json_serialization():
    """3. Test RedisCache adapter with mocked client verifying JSON serialization and TTL methods."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"account_id": "ACC-99", "balance": 45000.5}'
    mock_redis.exists.return_value = 1
    mock_redis.ttl.return_value = 285
    mock_redis.delete.return_value = 1

    adapter = RedisCache(client=mock_redis)
    assert adapter.is_connected

    # Get should parse JSON
    val = adapter.get("acc:99")
    assert val == {"account_id": "ACC-99", "balance": 45000.5}
    mock_redis.get.assert_called_with("acc:99")

    # Set should serialize to JSON and call setex if TTL provided
    assert adapter.set("acc:99", {"balance": 50000}, ttl_seconds=300)
    mock_redis.setex.assert_called_with(name="acc:99", time=300, value='{"balance": 50000}')

    # TTL and Delete
    assert adapter.get_ttl("acc:99") == 285
    assert adapter.delete("acc:99")
    mock_redis.delete.assert_called_with("acc:99")


def test_fixed_window_rate_limiter_allow_and_block():
    """4. Test distributed fixed-window rate limiter quota exhaustion and throttling."""
    limiter = DistributedRateLimiter()
    client_key = "analyst-app-token"
    limit = 5
    window_sec = 60

    req = RateLimitRequest(identifier=client_key, limit=limit, window_seconds=window_sec, cost=1)

    for i in range(1, limit + 1):
        res = limiter.check_rate_limit(req)
        assert res.allowed is True
        assert res.current_count == i
        assert res.remaining == limit - i

    # 6th request: exceeds quota and must be throttled
    blocked = limiter.check_rate_limit(req)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after is not None
    assert blocked.retry_after > 0


def test_rate_limiter_lua_script_syntax_and_structure():
    """5. Verify the production atomic Redis Lua script structure and commands."""
    script = REDIS_LUA_RATE_LIMITER
    assert "redis.call('INCRBY', key, cost)" in script
    assert "redis.call('EXPIRE', key, window)" in script
    assert "redis.call('TTL', key)" in script
    assert "return {allowed, current, limit, ttl}" in script
    assert "tonumber(ARGV[1])" in script


def test_tenant_scoped_idempotency_keys_and_replay():
    """6. Test tenant isolation, hashed idempotency keys, and response replay."""
    cache = MemoryCache()
    mgr = IdempotencyManager(cache, ttl_seconds=3600)

    tenant_a = "tenant-icici"
    tenant_b = "tenant-axis"
    idem_key = "transfer-tx-001"
    payload = {"source": "A", "dest": "B", "amount": 10000}

    # Tenant A reserves key
    is_new_a, rec_a = mgr.check_or_reserve(tenant_a, idem_key, payload)
    assert is_new_a is True
    assert rec_a.status == "IN_PROGRESS"

    # Tenant B with same key should be treated as completely independent (tenant isolation)
    is_new_b, rec_b = mgr.check_or_reserve(tenant_b, idem_key, payload)
    assert is_new_b is True
    assert rec_a.key_hash != rec_b.key_hash

    # Save completed result for Tenant A
    result_data = {"tx_id": "TX-1001", "status": "SETTLED"}
    mgr.save_result(tenant_a, idem_key, result_data)

    # Replay request for Tenant A: must return cached result with is_replayed=True
    is_new_replay, rec_replay = mgr.check_or_reserve(tenant_a, idem_key, payload)
    assert is_new_replay is False
    assert rec_replay.is_replayed is True
    assert rec_replay.status == "COMPLETED"
    assert rec_replay.response_payload["tx_id"] == "TX-1001"


def test_caching_service_health_and_metrics():
    """7. Test caching service health endpoint, metric calculations, and policy registry."""
    # Test through FastAPI client
    resp = client.get("/api/v1/caching/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["backend"] in ["memory", "redis"]
    assert "metrics" in data
    assert len(data["policies"]) >= 5

    # Test cache policies list
    pol_resp = client.get("/api/v1/caching/policies")
    assert pol_resp.status_code == 200
    policies = pol_resp.json()
    data_types = [p["data_type"] for p in policies]
    assert "Customer Profile" in data_types
    assert "Merchant Metadata" in data_types
    assert "Idempotency Response" in data_types
    assert "Rate-Limit Counter" in data_types

    # Test metrics endpoint
    metric_resp = client.get("/api/v1/caching/metrics")
    assert metric_resp.status_code == 200
    m_data = metric_resp.json()
    assert "hit_ratio" in m_data
    assert "hits" in m_data


def test_terraform_and_docker_compose_validation():
    """8. Test Terraform ElastiCache resource definitions and Docker Compose configuration."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    tf_main = base_dir / "infrastructure" / "terraform" / "phase39" / "main.tf"
    tf_vars = base_dir / "infrastructure" / "terraform" / "phase39" / "variables.tf"
    docker_compose = base_dir / "docker-compose.phase39.yml"

    assert tf_main.exists(), "Terraform main.tf must exist"
    assert tf_vars.exists(), "Terraform variables.tf must exist"
    assert docker_compose.exists(), "docker-compose.phase39.yml must exist"

    tf_content = tf_main.read_text(encoding="utf-8")
    assert "aws_elasticache_replication_group" in tf_content
    assert "aws_elasticache_parameter_group" in tf_content
    assert "at_rest_encryption_enabled" in tf_content
    assert "transit_encryption_enabled" in tf_content
    assert "automatic_failover_enabled" in tf_content

    # Validate docker compose syntax
    compose_yaml = docker_compose.read_text(encoding="utf-8")
    parsed_compose = yaml.safe_load(compose_yaml)
    assert "services" in parsed_compose
    assert "redis" in parsed_compose["services"]
    assert "image" in parsed_compose["services"]["redis"]
    assert "6379:6379" in parsed_compose["services"]["redis"]["ports"]

