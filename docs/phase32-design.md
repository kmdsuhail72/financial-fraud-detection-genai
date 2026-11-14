# Phase 32 — Enterprise API Gateway, Microservices Security, Multi-Tenant Architecture & Service-to-Service Communication

## 1. Overview
Phase 32 establishes a secure enterprise access layer and microservices gateway for FinGuard AI. It provides:
1. **API Gateway Routing & Versioning (`/api/v1`)**: Versioned routing surface with automated correlation ID propagation (`X-Request-ID`).
2. **Cryptographic JWT Authentication**: Token validation with RS256/HS256 fallback, strict issuer (`https://auth.finguard.internal`), audience (`finguard-api-gateway`), and expiry verification.
3. **Role-Based Access Control (RBAC)**: Fine-grained permissioning across `Admin`, `Investigator`, `Analyst`, and `Auditor` roles.
4. **Multi-Tenant Architecture**: Strict logical partitioning of cases, investigations, and analytical queries by `tenant_id`.
5. **Service-to-Service (S2S) Authentication**: Machine-to-machine validation using cryptographic preshared service keys (`X-Service-Key`).
6. **Sliding-Window Rate Limiting**: In-memory sliding log rate limiter returning HTTP `429 Too Many Requests` with `Retry-After` header.
7. **Gateway Observability**: Per-tenant metrics, request counters, route-level latency, and CloudWatch HTTP access logging.

---

## 2. Architecture & Components

```
Client / Microservice
        │
        ▼
[ API Gateway: /api/v1 ] ─── (X-Request-ID Correlation Middleware)
        │
        ├──► Rate Limiter (Sliding Window Log: 429 + Retry-After)
        ├──► S2S Validator (X-Service-Key Header Validation)
        └──► JWT Validator (PyJWT: Signature, Expiration, Issuer, Audience)
                │
                ▼
         [ AuthenticatedIdentity ]
         (user_id, tenant_id, role, scopes)
                │
                ├──► RBAC Guard (Admin / Auditor / Investigator / Analyst)
                └──► Multi-Tenant Scoping (Tenant-isolated queries)
```

---

## 3. Endpoints Implemented

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| GET | `/api/v1/health` | None | Gateway health, operational status, versioning info |
| POST | `/api/v1/auth/token` | None | Generates signed synthetic test JWT tokens for development |
| GET | `/api/v1/auth/me` | Bearer JWT | Decodes and returns currently authenticated identity claims |
| GET | `/api/v1/cases` | Bearer JWT | Returns case list strictly partitioned by the identity's `tenant_id` |
| POST | `/api/v1/cases` | Bearer JWT | Creates a new investigation case bound to the caller's `tenant_id` |
| POST | `/api/v1/service/echo` | S2S Key (`X-Service-Key`) | Inter-service secure communication ping/echo endpoint |
| GET | `/api/v1/admin/audit` | Bearer JWT (`Admin`, `Auditor`) | Restricted audit route requiring administrative role |
| GET | `/api/v1/rate-limit-test` | None | Test endpoint with strict rate limiting (3 req / 60s) |
| GET | `/api/v1/gateway/metrics` | None | Operational metrics: total requests, active tenants, rate limit counts |

---

## 4. Production Security Disclaimer
> [!NOTE]
> FinGuard AI uses synthetic identities, mock tokens, and an in-memory sliding-window log for local validation and testing. Production deployments must configure AWS API Gateway HTTP APIs with Cognito User Pool authorizers, KMS-managed keys, and Redis/ElastiCache sliding-window rate limiters.
