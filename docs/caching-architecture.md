# FinGuard AI — Caching Architecture Operations & Runbook

## 1. Operational Overview
The FinGuard Caching Tier operates across two deployment environments:
1. **Local & Test**: Thread-safe in-memory cache adapter (`MemoryCache`) with millisecond TTL enforcement, zero external dependencies, and fallback rate limiting.
2. **Production AWS**: Multi-AZ Amazon ElastiCache for Redis 7.1 replication group in AWS Mumbai (`ap-south-1`).

---

## 2. Cache Failure Mitigation Playbooks

### 2.1. Cache Penetration (Queries for Non-Existent Keys)
- **Problem**: Malicious clients query non-existent customer IDs in high volume, bypassing cache and overwhelming authoritative databases.
- **Remedy**: Cache-aside loader stores synthetic null / sentinel objects with a short TTL ($30\text{s}$), preventing repetitive database hits.

### 2.2. Cache Stampede / Thundering Herd
- **Problem**: High-concurrency requests hit a high-traffic key (e.g. popular merchant or exchange rate) at the exact moment its TTL expires.
- **Remedy**: Single-flight lock reservation or probabilistic early expiration (XFetch algorithm) in high-throughput microservices.

### 2.3. Cache Avalanche (Simultaneous Expiry)
- **Problem**: Many related keys written at the same timestamp expire at the exact same moment, causing a database CPU spike.
- **Remedy**: Add jitter ($\pm 10\%$) to standard TTL durations:
  $$\text{Effective TTL} = \text{Base TTL} \pm \text{Random}(0, 0.1 \times \text{Base TTL})$$

---

## 3. Real-Time Monitoring & Metrics

The platform exposes metrics via `/api/v1/caching/metrics` and Prometheus `/metrics`:

- `finguard_cache_hits_total`: Total count of cache hits.
- `finguard_cache_misses_total`: Total count of cache misses.
- `finguard_cache_hit_ratio`: Real-time percentage ($\text{hits} / (\text{hits} + \text{misses})$).
- `finguard_cache_evictions_total`: Evicted keys due to memory pressure.
- `finguard_cache_keys_total`: Active key volume.

### Operational SLOs
- **Target Hit Ratio**: $> 85\%$ for read-heavy customer profile routes.
- **P99 Cache Latency**: $< 2.0\text{ ms}$ over Redis cluster connection.
- **Throttling Accuracy**: $100\%$ atomic enforcement for distributed rate limits.

---

## 4. Runbook: Invalidation & Emergency Flush

### Manual Invalidation of Customer Profile
```bash
curl -X PUT http://localhost:8000/api/v1/caching/profile/CUST-1001 \
  -H "Content-Type: application/json" \
  -d '{"risk_tier": "CRITICAL"}'
```

### Emergency Flush (Cluster-Wide Cache Reset)
```bash
curl -X POST http://localhost:8000/api/v1/caching/flush
```
> [!WARNING]
> Flushing the cache in production causes immediate cache misses on all incoming requests. Monitor downstream database IOPS and replica health immediately after issuing a flush command.

