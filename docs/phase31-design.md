# FinGuard AI — Phase 31: Enterprise Data Integration, Banking APIs & External Financial Intelligence

## 1. Executive Summary
Phase 31 implements the enterprise integration foundation connecting FinGuard AI with core banking systems (CBS), payment gateway rails (e.g., Razorpay, Stripe, Adyen), external KYC/AML providers, and signed webhook intake channels. It standardizes ingestion into a canonical schema, enforces idempotency, executes bounded exponential retries, directs irrecoverable failures to a Dead-Letter Queue (DLQ), and maintains an immutable audit ledger.

---

## 2. Architecture & Data Flow

```
                      +---------------------------------------+
                      |       External Data Sources           |
                      |  - Core Banking System (CBS APIs)     |
                      |  - Payment Gateways (Razorpay/Stripe) |
                      |  - Signed Webhooks (HMAC-SHA256)      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         Provider Adapters             |
                      |  - CBS Account & Txn Normalizer       |
                      |  - Gateway Lifecycle Event Mapper     |
                      |  - Cryptographic Signature Verifier   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    Canonical Ingestion Pipeline       |
                      |  - Deduplication & Idempotency Key    |
                      |  - Exponential Retry & Backoff        |
                      |  - Dead-Letter Queue (DLQ) Fallback   |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             +--------------------+              +--------------------+
             |  Canonical Events  |              | Dead-Letter Queue  |
             |  (DynamoDB / S3)   |              | (Failed & Triaged) |
             +----------+---------+              +--------------------+
                        |
                        v
             +--------------------+
             | FinGuard Detection |
             | (Phases 1-30 AML,  |
             | Fraud, KYC, Risk)  |
             +--------------------+
```

---

## 3. Implemented Adapters & Protocols

| Module | Adapter Purpose | Schema / Transport |
| :--- | :--- | :--- |
| **Core Banking Adapter** | Normalizes account debits/credits, CIF IDs, channels (ATM, Branch, UPI) | JSON REST / Batch posting |
| **Payment Gateway Adapter**| Normalizes payment authorizations, captures, refunds, and chargebacks | Gateway Webhook / REST |
| **Signed Webhook Ingestion**| Authenticates callbacks using HMAC-SHA256 signatures (`X-Signature`) | HTTP Webhook with SHA-256 |
| **Canonical Normalizer** | Emits uniform `CanonicalEvent` with source, amount, and normalized payload | Enterprise Internal Model |
| **Idempotency Engine** | Prevents double-processing via unique idempotency keys | Redis / DynamoDB Index |
| **Retry & DLQ Handler** | Bounded retries with exponential backoff; dead-letter isolation | SQS DLQ / DynamoDB DLQ |
| **Audit & Metrics** | Real-time monitoring of ingestion rates, failures, and duplicates | FastAPI + React Dashboard |

---

## 4. Production Limitations

> [!IMPORTANT]
> **Advisory Standard & Mock Providers:**
> - Ingestion currently utilizes synthetic banking schemas and mock gateways. Production deployment requires live mTLS, OAuth2 client credentials, and direct core banking host connectivity.
> - Storage operates in-memory for testing; AWS S3 and DynamoDB Terraform templates provide the cloud foundation.
