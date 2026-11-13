# Phase 20 — Enterprise Real-Time Fraud Decision Engine, Intelligent Alert Prioritization & Unified Risk Orchestration

## 1. Executive Summary

Phase 20 delivers the unified orchestration apex of FinGuard AI: the **Enterprise Real-Time Fraud Decision Engine and Intelligent Alert Prioritization System**. 

Prior phases engineered specialized detection signals:
- **Phase 7:** Tabular Machine Learning (XGBoost / LightGBM fraud probabilities)
- **Phase 14:** User & Entity Behavior Analytics (UEBA anomaly scores & baseline deviation)
- **Phase 16–18:** Graph Intelligence & Graph Neural Networks (GraphSAGE topological embeddings & community risk)
- **Phase 19:** Temporal Sequence Learning (GRU micro-burst velocity & time-decay features)
- **Phase 13:** Threat Intelligence (External IP/domain IOC reputation & MITRE ATT&CK techniques)

Phase 20 fusions these disparate, heterogeneous signals into a single, explainable, prioritized fraud decision. It features **dynamic weight renormalization** for graceful partial degradation, **configurable risk policies with threshold-based action routing**, **strict idempotent deduplication**, and **comprehensive explainability breakdown**.

> [!IMPORTANT]
> **Human-in-the-Loop Advisory Standard:**
> All composite risk scores, policy classifications (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), priority assignments (`P0`–`P3`), and recommended actions are **strictly advisory**. Final decisions—especially account freezes, merchant blocks, or law-enforcement escalations—remain governed by human SOC analysts and fraud investigation specialists.

---

## 2. Architecture & Orchestration Flow

```mermaid
flowchart TD
    subgraph Multi-Signal Inputs
        S1["ML Fraud Model (Phase 7)<br/>Default: 35%"]
        S2["UEBA Anomaly Engine (Phase 14)<br/>Default: 20%"]
        S3["Graph Intelligence / GNN (Phases 16-18)<br/>Default: 20%"]
        S4["Temporal Sequence Model (Phase 19)<br/>Default: 15%"]
        S5["Threat Intel & IOC (Phase 13)<br/>Default: 10%"]
    end

    subgraph Risk Fusion Engine
        VAL[Signal Validation & Clamping [0, 1]]
        RENORM[Dynamic Weight Renormalization<br/>w'_s = w_s / sum(w_active)]
        COVERAGE[Signal Coverage Calculation<br/>(Present / 5) * 100%]
        COMPOSITE[Composite Score Aggregation<br/>Score = sum(w'_s * score_s)]
    end

    subgraph Decision & Policy Engine
        POLICY[(Active Risk Policy Config<br/>POL-DEFAULT-V1)]
        THRESH[Threshold Interval Mapping]
        PRIO[Priority Tier Assignment: P0, P1, P2, P3]
        ACTION[Action Determination: Escalation / Challenge / Monitor / Approve]
    end

    subgraph Explainability & Attribution
        ATTR[Percentage Contribution Breakdown]
        REASONS[Dynamic Explainable Risk Reasons]
    end

    subgraph Storage & Infrastructure
        STORE[(Idempotent Local DecisionStore<br/>O(1) In-Memory Cache)]
        DDB[(AWS DynamoDB Table<br/>finguard-fraud-decisions)]
    end

    S1 & S2 & S3 & S4 & S5 --> VAL
    VAL --> RENORM
    RENORM --> COMPOSITE
    VAL --> COVERAGE
    COMPOSITE & POLICY --> THRESH
    THRESH --> PRIO & ACTION
    COMPOSITE & VAL --> ATTR --> REASONS
    PRIO & ACTION & REASONS & COVERAGE --> STORE
    STORE -.-> DDB
```

---

## 3. Mathematical Formulation of Risk Fusion

### 3.1 Static Base Weights
Let $\mathcal{S} = \{\text{ML}, \text{UEBA}, \text{Graph}, \text{Temporal}, \text{ThreatIntel}\}$ be the set of available detection signals with predefined default weights:

$$\mathbf{w}_{\text{base}} = [0.35, 0.20, 0.20, 0.15, 0.10], \quad \sum_{s \in \mathcal{S}} w_s = 1.00$$

### 3.2 Dynamic Weight Renormalization
In real-time production environments, network timeouts, offline dependencies, or cold starts may cause one or more upstream signal engines to fail to return scores within strict SLA windows (<50ms). Rather than failing or defaulting missing signals to zero (which would falsely depress composite fraud risk), the Risk Fusion Engine isolates active signals $\mathcal{S}_{\text{present}} \subseteq \mathcal{S}$:

$$W_{\text{active}} = \sum_{s \in \mathcal{S}_{\text{present}}} w_s$$

Effective weights are dynamically normalized:

$$w'_s = \frac{w_s}{W_{\text{active}}} \quad \forall s \in \mathcal{S}_{\text{present}}, \quad \sum_{s \in \mathcal{S}_{\text{present}}} w'_s = 1.00$$

The composite risk score $R$ is computed as:

$$R = \sum_{s \in \mathcal{S}_{\text{present}}} w'_s \cdot \sigma_s, \quad \sigma_s \in [0, 1]$$

### 3.3 Signal Coverage Metric
To quantify signal reliability and audit data completeness, signal coverage is reported alongside every decision:

$$\text{Coverage} = \left( \frac{|\mathcal{S}_{\text{present}}|}{|\mathcal{S}|} \right) \times 100\%$$

---

## 4. Policy Configuration, Thresholds & Actions

The decision engine maps the composite risk score $R \in [0.0, 1.0]$ into standardized classification tiers, priority queues, and recommended actions:

| Risk Score Interval | Classification | Priority Tier | Recommended Action | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0.00 – 0.35** | `LOW` | **P3** | `APPROVE` | Normal consumer transaction; logged for audit. |
| **0.35 – 0.70** | `MEDIUM` | **P2** | `MONITOR` | Elevated anomaly signals; flagged for ambient monitoring. |
| **0.70 – 0.90** | `HIGH` | **P1** | `CHALLENGE` | Strong fraud indicators; prompt Step-up MFA / OTP. |
| **0.90 – 1.00** | `CRITICAL` | **P0** | `ESCALATE` | Coordinated attack or fraud ring; immediate SOC dispatch. |

Policies are version-controlled (`POL-DEFAULT-V1`, `2026.11-v1`) and support dynamic hot-reloading at runtime via REST APIs without service restart.

---

## 5. Signal Explainability & Risk Attribution

For regulatory compliance (FCRA, GDPR, OCC Guidance), black-box decisions are rejected. FinGuard AI generates:

1. **Relative Signal Contribution:**
   $$\text{Attribution}_s = \frac{w'_s \cdot \sigma_s}{\sum_{i \in \mathcal{S}_{\text{present}}} w'_i \cdot \sigma_i} \times 100\%$$
2. **Deterministic Risk Reasons:** Plain-language justifications grounded in empirical deviations:
   - *"Critical composite risk score: 0.91 exceeding high-risk threshold (0.90)"*
   - *"Temporal Sequence model flagged rapid micro-burst velocity (score: 0.94)"*
   - *"Graph GNN identified dense community ties to known fraud rings (score: 0.88)"*
   - *"High-confidence threat intelligence hit on known malicious proxy/botnet (score: 0.95)"*

---

## 6. Idempotent Storage & Infrastructure

### 6.1 Deduplication & Idempotency
Transactions may be retransmitted across network retries. `DecisionStore` guarantees:
- **Idempotency Key:** Strict deduplication keyed by `transaction_id`.
- **Duplicate Handling:** Repeated requests return the identical, original decision timestamp and payload without recomputing or corrupting state.
- **Query Efficiency:** Secondary indexes enable instant lookups by `priority` (`P0`–`P3`), `classification`, and chronological order.

### 6.2 AWS DynamoDB Infrastructure (Terraform)
Located in `infrastructure/terraform/phase20/`:
- **Primary Table:** `finguard-fraud-decisions`
- **Partition Key:** `transaction_id` (String)
- **Global Secondary Indexes:**
  - `PriorityIndex`: Partition Key `priority`, Sort Key `created_at`
  - `ClassificationIndex`: Partition Key `classification`, Sort Key `created_at`
- **Security & Durability:** Server-Side Encryption with AWS KMS (SSE-KMS), Point-in-Time Recovery (PITR), and automatic TTL on `expires_at`.

---

## 7. REST API Specifications

The decision service exposes high-throughput endpoints on `/decisions`:

- `POST /decisions`: Evaluates risk across provided signals and returns structured decision.
- `GET /decisions`: Retrieves decision history with optional filtering by `priority`, `classification`, and `limit`.
- `GET /decisions/{id}`: Retrieves specific decision record by transaction ID.
- `GET /decisions/health`: Verifies decision engine and store operational status.
- `GET /decisions/policies/active`: Inspects current policy thresholds and weights.
- `PUT /decisions/policies/active`: Updates policy thresholds and weights with validation.

### Sample Execution Payload
```bash
curl -X POST http://127.0.0.1:8010/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-PHASE20-DEMO-001",
    "customer_id": "CUST-9824",
    "amount": 4850.00,
    "currency": "USD",
    "signals": {
      "ml_fraud_score": 0.89,
      "ueba_anomaly_score": 0.74,
      "graph_fraud_probability": 0.92,
      "temporal_sequence_score": 0.85,
      "threat_intel_risk": 0.90
    }
  }'
```

---

## 8. Validation Results

| Test Case | Description | Verification Status |
| :--- | :--- | :--- |
| `test_health_endpoint` | Verifies health check returns 200 and healthy status | **PASSED** |
| `test_full_signals_critical_decision` | Verifies 5-signal fusion, P0 critical classification, and 100% coverage | **PASSED** |
| `test_low_risk_decision` | Verifies low fraud score triggers P3 LOW APPROVE | **PASSED** |
| `test_missing_signals_renormalization` | Validates weight renormalization when Temporal and Threat Intel are omitted | **PASSED** |
| `test_idempotent_decision_store` | Verifies identical transaction returns idempotent cached decision | **PASSED** |
| `test_policy_update_endpoint` | Verifies active policy update and immediate effect | **PASSED** |
| `test_list_decisions_with_filter` | Verifies query filtering by priority tier and pagination | **PASSED** |
| `test_get_decision_by_id` | Verifies direct transaction ID lookup | **PASSED** |
| `test_single_signal_fallback` | Validates graceful degradation when only 1 signal is supplied | **PASSED** |

**Summary: 9/9 Tests Passed (100% Success Rate)**

