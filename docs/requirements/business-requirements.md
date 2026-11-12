# FinGuard AI — Business Requirements Specification

## 1. Problem Statement & Financial Context
Financial institutions process millions of daily electronic payments across credit/debit card rails, instant transfer networks (UPI, IMPS, FedNow, SEPA), and ATM networks. Fraud topologies have evolved from simple stolen card numbers to coordinated velocity attacks, synthetic identity creation, and credential stuffing account takeovers (ATO).

Traditional fraud detection infrastructure relies on static heuristic rules (e.g., *"Flag if amount > 50,000 INR"*), resulting in:
- **Excessive False Positive Rates (FPR):** 90–95% of rule alerts are legitimate customer transactions, creating operational friction and false declines that erode customer trust.
- **Investigation Backlogs:** Investigators spend an average of 45 to 90 minutes per case manually assembling transaction history, device changes, and geolocation logs.
- **Delayed Intervention:** Rule evaluation often happens asynchronously or downstream in nightly settlement batches, allowing fraudulent funds to leave the institution before intervention.
- **Inability to Adapt to Novel Fraud Vectors:** Fraud rings continuously modify transaction velocity and amounts to slip beneath static thresholds.

---

## 2. Platform Objectives & Success Criteria

### Core Business Goals
1. **Reduce False Positives:** Lower the false-positive alert volume by at least 40% compared to traditional rule-based baselines using dual-model machine learning.
2. **Accelerate Investigator Throughput:** Reduce average case investigation triage time from 60 minutes to under 5 minutes using grounded Amazon Bedrock GenAI summaries.
3. **Sub-5 Second Ingestion-to-Decision:** Intercept suspicious payments in flight before final financial clearance.
4. **Complete Auditability:** Satisfy regulatory compliance (e.g., RBI guidelines, PCI-DSS, SOC-2) with immutable audit logs recording every alert, feature vector, AI generation, and analyst decision.

---

## 3. High-Level Business Metrics & KPIs

| Business Metric | Baseline (Legacy Rules) | FinGuard AI Target | Measurement Method |
| :--- | :--- | :--- | :--- |
| **False Positive Ratio (FPR)** | 92% | < 45% | Percentage of closed alerts marked "False Positive" |
| **Time to Triage Case (MTTI)** | 55 minutes | < 5 minutes | Time from alert creation to investigator review |
| **Fraud Detection Precision** | ~ 8% | > 40% | True Positives / (True Positives + False Positives) |
| **Fraud Recall** | ~ 60% | > 85% | Captured fraudulent value / Total fraudulent value |
| **Audit Trail Completeness** | Manual notes | 100% automated | System-logged timestamps, user IDs, decisions |
