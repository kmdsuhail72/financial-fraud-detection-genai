# FinGuard AI — Phase 29: Enterprise Payment Fraud Intelligence & Real-Time Monitoring

## 1. Executive Summary
Phase 29 introduces real-time payment fraud detection, multi-rail transaction monitoring, payment gateway risk analytics, and velocity-based anomaly identification to FinGuard AI. The module evaluates transactions across Indian domestic and international payment rails (`UPI`, `IMPS`, `NEFT`, `RTGS`, and `CARD`), calculating an explainable 0–100 risk score and assigning human-in-the-loop operational actions (`MONITOR`, `REVIEW`, `PRIORITY_REVIEW`).

---

## 2. Architecture & Data Flow

```
                      +------------------------------------------+
                      | Payment Gateways / Core Banking Ingestion|
                      |  (UPI, IMPS, NEFT, RTGS, Card Networks)   |
                      +--------------------+---------------------+
                                           |
                                           v
                             +----------------------------+
                             | Schema & Event Validation  |
                             |  - Amount & Currency       |
                             |  - Beneficiary Identity    |
                             |  - Device Context Telemetry|
                             +-------------+--------------+
                                           |
                                           v
                             +----------------------------+
                             | Payment Intelligence Engine|
                             |  1. High-Value Payment     |
                             |  2. New Beneficiary Payee  |
                             |  3. City & Geo Mismatch    |
                             |  4. Rolling 10m Velocity   |
                             |  5. Cross-Border / Intl    |
                             |  6. Missing Device Finger  |
                             +-------------+--------------+
                                           |
                                           v
                             +----------------------------+
                             | Explainable Risk Score     |
                             |  - Range: 0 to 100         |
                             |  - Actions:                |
                             |    * MONITOR (< 30)        |
                             |    * REVIEW (30 - 69)      |
                             |    * PRIORITY_REVIEW (>=70)|
                             +-------------+--------------+
                                           |
                       +-------------------+-------------------+
                       |                                       |
                       v                                       v
             +--------------------+                 +--------------------+
             | FastAPI Endpoints  |                 | React Analyst UI   |
             |  /payments/assess  |                 | Real-time Stream & |
             |  /payments/metrics |                 | Risk Inspector     |
             +--------------------+                 +--------------------+
```

---

## 3. Signal Scoring Matrix & Rules

| Signal ID | Risk Factor | Points | Evaluation Condition |
| :--- | :--- | :---: | :--- |
| **SIG-HV** | High-Value Payment | **20** | `amount >= ₹2,00,000.00` |
| **SIG-NB** | New Beneficiary | **15** | `is_new_beneficiary == True` |
| **SIG-GM** | City Mismatch | **10** | `customer_home_city != transaction_city` |
| **SIG-VL** | Velocity Anomaly | **25** | $\ge 3$ transactions in rolling 10-minute window |
| **SIG-CB** | International Flow | **20** | `is_international == True` or non-domestic currency |
| **SIG-DV** | Missing Device Context | **15** | `device_context` is null or `device_id` is missing |

**Composite Score Formulation:**
$$\text{Score} = \min\left(100, \sum_{s \in \text{Triggered Signals}} \text{Points}(s)\right)$$

**Benchmark Example Validation:**
- Transaction: ₹2,85,000 via UPI
- Payee: New Beneficiary
- Geographic: Bengaluru (Home) $\rightarrow$ Mumbai (Transaction)
- Device: Authenticated Android Device present
- **Calculation:** High-Value ($20$) + New Beneficiary ($15$) + City Mismatch ($10$) = **45 / 100**
- **Classification:** **MEDIUM**
- **Action:** **REVIEW**

---

## 4. Alert Prioritization Tiers

| Score Range | Risk Level | Operational Action | Analyst SLA / Protocol |
| :---: | :---: | :---: | :--- |
| **0 – 29** | `LOW` | `MONITOR` | Passive audit logging; automatic transaction release |
| **30 – 69** | `MEDIUM` | `REVIEW` | Queue for human analyst triage within 15 minutes |
| **70 – 100** | `HIGH` | `PRIORITY_REVIEW` | Immediate P0 alert dispatched to Fraud Ops desk |

---

## 5. Advisory Standard & Regulatory Governance

> [!IMPORTANT]
> **Human-in-the-Loop Standard:** All payment risk scores, signal points, and action recommendations are advisory operational tools. FinGuard AI does not perform automated transaction rejection, funds reversal, or account freezing. All mitigation decisions require affirmative human review.

