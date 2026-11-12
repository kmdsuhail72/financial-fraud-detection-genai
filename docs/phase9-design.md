# Phase 9: React Fraud Analyst Dashboard & Enterprise Investigation Portal

## 1. Overview & Architectural Role

Phase 9 delivers the analyst-facing frontend for **FinGuard AI**. Built with **React 18**, **TypeScript**, **Tailwind CSS**, and **Vite**, the application provides real-time fraud monitoring, triage, queue management, and deep investigation workflows powered by Amazon SageMaker risk scoring and Amazon Bedrock GenAI synthesis.

```
                    +------------------------------------------+
                    |  FinGuard AI Analyst Portal (Port 5173)  |
                    |  React 18 + Vite + TypeScript + Tailwind |
                    +--------------------+---------------------+
                                         |
                       Vite Proxy / Nginx reverse proxy
                                         |
                                         v
                    +------------------------------------------+
                    |       FastAPI Backend (Port 8001)        |
                    +--------------------+---------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-------------------------------+               +----------------------------------+
|    Amazon DynamoDB Tables     |               |      Amazon Bedrock GenAI        |
| - Cases & Audit Trail         |               | - Claude 3.5 Sonnet Synthesis    |
| - SageMaker Decision Store    |               | - Strict Grounded Evidence       |
+-------------------------------+               +----------------------------------+
```

---

## 2. Key Modules & Functional Capabilities

### A. Executive Fraud Overview (`/dashboard`)
- **Key Performance Indicators (KPIs):** Total Active Cases, Critical Risk Alerts, In-Review Triage, Resolved Today.
- **Risk Severity Decomposition:** Real-time distribution across Critical ($R > 0.85$), High ($0.70 - 0.85$), and Review ($0.50 - 0.70$) thresholds.
- **Channel Attack Surface:** Comparative breakdown of card fraud, UPI transaction velocity, NetBanking takeover attempts, and ATM anomalies.
- **Priority Queue Preview:** Top suspicious transactions with one-click direct investigation dispatch.

### B. Live Investigation Queue (`/queue`)
- **Real-Time Triage:** Comprehensive case listing with search across Case ID, Customer ID, Account ID, and Merchant name.
- **Multi-Dimensional Filters:** Filter by Case Status (`OPEN`, `IN_REVIEW`, `ESCALATED`, `RESOLVED`, `CLOSED`), Priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and Risk Level.
- **Interactive Sorting:** Instant sorting by Composite Risk Score, Transaction Amount, or Ingestion Timestamp.

### C. Case Investigation Dossier (`/detail`)
- **Transaction Dossier:** Deep transaction telemetry including Channel, Amount, MCC, Origin Geo, IP address, and Device Fingerprint.
- **Quantitative ML Decomposition:**
  - Composite Risk Score: $R = 0.65 \times P(\text{Fraud}) + 0.35 \times \text{Anomaly}$
  - Model weights: Supervised XGBoost probability vs. Unsupervised Isolation Forest outlier score.
  - Ingestion behavioral signals: Velocity (1h), Amount Ratio to historical average, distance from home, device familiarity.
- **Bedrock GenAI Copilot (`AiAssistantCard`):**
  - Executive synthesis summarizing transaction evidence.
  - Identified risk indicators.
  - Plausible legitimate alternative hypotheses (e.g. verified travel).
  - Recommended SOP Next Actions with interactive checkbox tracking.
- **Investigator Binding Verdict & Audit Trail:**
  - Human-in-the-Loop governance controls: Mark as Confirmed Fraud & Freeze, Mark as False Positive & Release, Escalate to Tier-2 AML, Hold for Customer Outbound.
  - Case notes journal with timestamps and author tagging.
  - Immutable audit trail recording state transitions.

### D. Governance & Sandbox Settings (`/settings`)
- **Demo Mode Switch:** Seamless zero-setup offline sandbox loaded with pre-packaged realistic banking fraud scenarios.
- **API URL Configuration & Connectivity Health Check:** Direct real-time latency ping to the backend FastAPI service.
- **AWS Cloud Telemetry:** Live mapping of AWS region (`ap-south-1`), SageMaker endpoint, and DynamoDB case stores.

---

## 3. Human-in-the-Loop Governance Standard

In adherence to banking regulatory compliance:
1. **ML Model Autonomy Restriction:** The SageMaker models compute risk probabilities; they do not block bank accounts or freeze credit lines autonomously.
2. **GenAI Advisory Separation:** Bedrock Claude 3.5 Sonnet generates evidence synthesis and recommended SOP checklists; it never issues binding legal declarations of guilt.
3. **Analyst Final Authority:** Only authenticated human investigators can resolve cases, dismiss alerts, or initiate financial remediation.

