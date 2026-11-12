# FinGuard AI — System Architecture Specification

## 1. Architectural Philosophy & Design Principles
The FinGuard AI platform is engineered to resolve systemic challenges in financial fraud operations:
- **Low-Latency Streaming:** Sub-5 second total latency from ingestion to risk evaluation.
- **Explainability & Traceability:** Strict separation between numerical machine learning risk models and GenAI narrative generation.
- **Auditability & Compliance:** Tamper-evident logging of all human decisions, model scores, and AI recommendations.
- **Loose Coupling:** Clean modular interfaces allowing independent scaling and lifecycle management of ingestion, ML inference, API, and frontend layers.

---

## 2. 8-Layer Enterprise Architecture

```mermaid
graph TD
    subgraph "Layer 1: Ingestion & Transaction Sources"
        TS[Transaction Simulator]
        API_IN[Edge Payment API Gateway]
    end

    subgraph "Layer 2: Streaming Ingestion"
        KDS[Amazon Kinesis Data Streams]
        DLQ[Kinesis Dead Letter Queue / SQS]
    end

    subgraph "Layer 3: Processing & Real-Time Feature Engineering"
        LAMBDA[AWS Lambda Stream Processor]
        CACHE[(Redis / DynamoDB Feature Store)]
    end

    subgraph "Layer 4: Data Lake (Medallion)"
        S3_BRONZE[(S3 Bronze: Raw JSON)]
        GLUE[AWS Glue ETL / Catalog]
        S3_SILVER[(S3 Silver: Parquet Cleaned)]
        S3_GOLD[(S3 Gold: Analytical Aggregates)]
        ATHENA[Amazon Athena SQL Engine]
    end

    subgraph "Layer 5: Intelligent Fraud Detection"
        SAGEMAKER[Amazon SageMaker Endpoint]
        XGB[XGBoost Supervised Classification]
        IF[Isolation Forest Anomaly Detection]
        RE[Unified Risk Engine R = 100 * (0.65P + 0.35A)]
    end

    subgraph "Layer 6: GenAI Investigation"
        BEDROCK[Amazon Bedrock - Claude 3]
        PROMPTS[Grounded Evidence Assembler]
        GUARD[Output Schema Guardrails]
    end

    subgraph "Layer 7: Application & Human-in-the-Loop"
        FASTAPI[FastAPI Backend Services]
        RDS[(Amazon RDS PostgreSQL)]
        REACT[React Investigator Workbench]
    end

    subgraph "Layer 8: Governance & Security"
        KMS[AWS KMS Envelope Encryption]
        IAM[IAM Least-Privilege Policies]
        CW[CloudWatch Alarms & CloudTrail]
    end

    TS -->|JSON Batch| KDS
    API_IN -->|JSON Event| KDS
    KDS -->|Event Stream| LAMBDA
    KDS -.->|Poison Pills| DLQ
    LAMBDA <-->|Fetch/Write Velocity| CACHE
    LAMBDA -->|Raw Persist| S3_BRONZE
    S3_BRONZE --> GLUE --> S3_SILVER --> S3_GOLD
    S3_GOLD -.-> ATHENA
    LAMBDA -->|Enriched Vector| SAGEMAKER
    SAGEMAKER --> XGB & IF
    XGB & IF --> RE
    RE -->|Score & Decision| FASTAPI
    FASTAPI -->|Write Case & Alert| RDS
    FASTAPI -->|Trigger Investigation| PROMPTS
    PROMPTS --> BEDROCK --> GUARD --> FASTAPI
    FASTAPI <-->|REST / WS| REACT
```

---

## 3. Layer Breakdown and Responsibilities

### Layer 1: Transaction Sources & Simulation
- **Simulator Framework:** Generates realistic synthetic transactions across Card Present (POS), Card Not Present (e-Commerce), ATM withdrawals, and Wire/IMPS transfers.
- **Fraud Injectors:** Implements distinct attack archetypes:
  1. *Account Takeover (ATO):* Rapid device changes followed by maximum account balance drain.
  2. *Card Testing:* Succession of small micro-transactions followed by an expensive electronics purchase.
  3. *Impossible Travel:* Geographically impossible physical transactions within a 15-minute window.
  4. *Bursty Velocity:* Rapid transactions exceeding normal standard deviations within 5-minute rolling windows.

### Layer 2: Streaming Ingestion (Amazon Kinesis)
- **Sharding Strategy:** Partitioned by `account_id` to guarantee sequential consistency of financial transactions per customer.
- **Retention:** Configured with a 7-day retention period allowing reprocessing during incident recovery.
- **Backpressure & Dead Letter:** Malformed messages are directed to an SQS Dead-Letter Queue (DLQ) after 3 retry attempts.

### Layer 3: Serverless Processing & Feature Store (AWS Lambda)
- **Validation:** JSON Schema enforcement on every inbound payload.
- **Deduplication:** Uses `transaction_id` hashing with a short-term sliding window.
- **Dynamic Velocity Features:** Computes rolling aggregations:
  - `avg_amount_24h`
  - `transaction_count_5m`
  - `transaction_count_1h`
  - `amount_deviation_score`
  - `new_device_flag`
  - `international_flag`

### Layer 4: Medallion Data Lake (Amazon S3 & AWS Glue)
- **Bronze Tier:** Unaltered raw JSON stream outputs partitioned by `year=YYYY/month=MM/day=DD/hour=HH`.
- **Silver Tier:** Schema-validated, deduplicated Apache Parquet format optimized for columnar reads.
- **Gold Tier:** Curated feature marts containing labeled fraud sets for automated model retraining.

### Layer 5: Intelligent Dual-Model Detection (SageMaker)
- **Supervised Classifier (XGBoost):** Outputs calibrated probability $P \in [0, 1]$ representing likelihood of known fraud patterns.
- **Unsupervised Anomaly Model (Isolation Forest):** Outputs normalized anomaly score $A \in [0, 1]$ identifying outliers in high-dimensional feature space.
- **Unified Risk Calculation:**
  $$R = 100 \times (0.65 \times P + 0.35 \times A)$$
- **Decoupled Scoring Decision:** High-risk transactions trigger case generation; low-risk transactions proceed directly to settlement.

### Layer 6: GenAI Investigation Copilot (Amazon Bedrock)
- **Core Principle:** GenAI **never** decides whether a transaction is fraudulent.
- **Functionality:** Ingests the model prediction vector, velocity features, merchant context, and customer historical baseline to draft:
  1. Executive Case Summary.
  2. Grounded Evidence Bullets (citing specific values, e.g., "Amount is 4.8x the 30-day average").
  3. Recommended Investigator Next Steps.
- **Guardrails:** Bedrock output is strictly parsed and validated against a Pydantic schema before persistence.

### Layer 7: Case Management & APIs (FastAPI + React)
- **FastAPI Core:** Provides asynchronous endpoints for transaction scoring, alert triage, case assignment, decision recording, and metrics reporting.
- **React Frontend:** Enterprise dashboard featuring:
  - Real-time live fraud feed.
  - Case detail view with Bedrock AI narrative panel.
  - Interactive feature radar charts and timeline visualizations.
  - Investigator human decision panel (Approve / Decline / Escalate to Law Enforcement).

### Layer 8: Governance, Security & Observability
- **Encryption:** All storage (S3, RDS, EBS) encrypted with customer-managed AWS KMS keys.
- **Role-Based Access Control (RBAC):** Distinct roles (Admin, Fraud Analyst, Investigator, Auditor, Data Engineer, ML Engineer).
- **Audit Logs:** Every status change, assignment, and decision is stored in an append-only PostgreSQL table.

