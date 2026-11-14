# Phase 39 — Enterprise Caching Architecture, Redis, Amazon ElastiCache, Distributed Rate Limiting & High-Performance Data Access

## 1. Executive Summary

Phase 39 introduces an enterprise-grade distributed caching and coordination layer for **FinGuard AI**. By deploying Redis (local development) and Amazon ElastiCache for Redis (production in `ap-south-1` Mumbai), the platform achieves sub-millisecond data retrieval for frequent fraud-scoring queries, eliminates duplicate transactions via tenant-isolated idempotency keys, and enforces atomic distributed rate limiting across microservice replicas.

---

## 2. Architecture & Topology

```
+-------------------------------------------------------------------------------+
|                             FinGuard API Gateway                              |
|               (Transaction, Fraud Scoring, Customer, AML APIs)                |
+---------------------------------------+---------------------------------------+
                                        |
                 +----------------------+----------------------+
                 | Cache-Aside Read/Write                      | Rate Limiting & Idempotency
                 v                                             v
+-------------------------------------------------------------------------------+
|                    Redis / Amazon ElastiCache Multi-AZ                        |
|  - Customer Profiles (TTL: 5m)             - Merchant Metadata (TTL: 15m)     |
|  - Rate Limit Counters (TTL: 60s)          - Idempotency Records (TTL: 24h)   |
|  - Transaction Lookups (TTL: 1m)           - Atomic Lua Script Engine         |
+---------------------------------------+---------------------------------------+
                                        | (Cache Miss / Invalidation)
                                        v
+-------------------------------------------------------------------------------+
|                         Authoritative Data Stores                             |
|          Amazon DynamoDB · Amazon RDS PostgreSQL · S3 Data Lake               |
+-------------------------------------------------------------------------------+
```

### ElastiCache Production Topology
- **Engine**: Redis 7.1 with in-transit TLS and at-rest KMS encryption.
- **Node Type**: `cache.t4g.medium` (Graviton2 ARM architecture for cost/performance optimization).
- **High Availability**: Multi-AZ replication group with automatic failover across 2 subnets.
- **Eviction Policy**: `volatile-lru` — entries with an explicit TTL are evaluated under memory pressure, preserving persistent configuration keys.

---

## 3. Core Capabilities

### 3.1. Cache-Aside (Read-Through) Primitives
1. **Customer Profile Queries**:
   - Check cache under key `profile:{customer_id}`.
   - On cache miss, fetch authoritative customer risk record from DynamoDB/RDS.
   - Populate cache with standard 5-minute TTL ($300\text{s}$).
2. **Explicit Invalidation**:
   - When customer risk tier, country, or KYC status is updated, the API writes to the database and immediately deletes `profile:{customer_id}`.
   - Prevents stale fraud evaluations from scoring new payments.

### 3.2. Atomic Distributed Rate Limiting (Redis Lua)
To avoid race conditions and clock drifts across multiple API containers, rate limiting is executed via an atomic Lua script directly in Redis memory:
```lua
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local cost = tonumber(ARGV[3]) or 1

local current = redis.call('INCRBY', key, cost)
if current == cost then
    redis.call('EXPIRE', key, window)
end

local ttl = redis.call('TTL', key)
if ttl < 0 then
    redis.call('EXPIRE', key, window)
    ttl = window
end

local allowed = 0
if current <= limit then
    allowed = 1
end

return {allowed, current, limit, ttl}
```
If Redis is temporarily disconnected or in local offline mode, the system automatically falls back to an in-memory sliding fixed-window algorithm with thread locks.

### 3.3. Tenant-Scoped Idempotency
- **Key Derivation**: SHA-256 hash of `f"tenant:{tenant_id}:key:{idempotency_key}"`.
- **Payload Verification**: Computes SHA-256 hash of the request payload to ensure that replayed requests with altered amounts or destinations are rejected with payload mismatch errors.
- **Replay State**: Operations are initially reserved in `IN_PROGRESS` status, updated to `COMPLETED` once processed, and preserved for 24 hours ($86,400\text{s}$) to replay identical responses to clients without redundant scoring computation.

---

## 4. Standard Enterprise Cache Policies

| Data Classification | Key Pattern | TTL | Eviction / Invalidation Trigger | Usage Guideline |
| :--- | :--- | :--- | :--- | :--- |
| **Customer Profile** | `profile:{id}` | 5 min ($300\text{s}$) | Profile update or KYC re-screening | Core fraud feature vector |
| **Merchant Metadata** | `merchant:{id}` | 15 min ($900\text{s}$) | Merchant MCC or risk status update | High-throughput payment routing |
| **Transaction Lookup** | `tx_lookup:{id}` | 1 min ($60\text{s}$) | Time-to-live expiration | Fast deduplication and settlement checks |
| **Idempotency Record**| `idempotency:{hash}`| 24 hours ($86400\text{s}$) | Time-to-live expiration | Multi-tenant duplicate prevention |
| **Rate Limit Counter**| `rate_limit:{id}:{w}`| 60 sec ($60\text{s}$) | Window expiration | DDoS and API abuse prevention |

> [!CAUTION]
> **Financial Ledger Boundary**: Never use Redis as the authoritative financial ledger or as the sole storage for final compliance decisions. All financial mutations must be durably committed to ACID/ACID-like stores before or concurrently with cache writes.

---

## 5. Verification & Testing

- **Smoke Script**: Standalone verification via `python scripts/smoke_cache.py`.
- **Test Suite**: 8/8 comprehensive pytest test cases covering memory cache, cache-aside read-through, profile invalidation, Redis serialization, Lua rate limiting, tenant idempotency, metrics endpoints, and Terraform infrastructure validation.
