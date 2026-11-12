# FinGuard AI — Functional Requirements Specification

## 1. Functional Requirements Matrix (FR-01 to FR-15)

| Requirement ID | Requirement Title | Priority | Description & Acceptance Criteria |
| :--- | :--- | :---: | :--- |
| **FR-01** | Realistic Transaction Simulation | **Critical** | The system must generate synthetic banking transactions with realistic distributions across amounts, merchant categories, payment channels, geographic locations, and customer profiles. It must support injecting specific fraud archetypes (ATO, card testing, sudden velocity). |
| **FR-02** | Real-Time Kinesis Streaming | **Critical** | The system must ingest transaction events via Amazon Kinesis Data Streams. Partitioning must occur by `account_id` to preserve event ordering. |
| **FR-03** | Serverless Event Validation | **Critical** | AWS Lambda must validate every incoming transaction against a strict JSON Schema, discard or redirect malformed payloads to a Dead-Letter Queue (DLQ), and guarantee idempotent processing. |
| **FR-04** | Real-Time Feature Engineering | **Critical** | Lambda must compute rolling customer velocity metrics (1m, 5m, 1h, 24h spending aggregates, device changes, location changes, and deviation from customer baseline) with sub-second lookup latency. |
| **FR-05** | Medallion S3 Data Lake | **Critical** | Transactions must be stored in Amazon S3 following the Medallion architecture (Bronze raw JSON, Silver cleansed Parquet, Gold curated feature marts for training). |
| **FR-06** | Supervised Fraud Classification | **Critical** | The platform must deploy an XGBoost model in SageMaker predicting fraud probability $P \in [0, 1]$ based on historical and velocity features. |
| **FR-07** | Unsupervised Anomaly Detection | **High** | The platform must run an Isolation Forest model in SageMaker calculating normalized anomaly score $A \in [0, 1]$ to detect novel fraud topologies without labeled data. |
| **FR-08** | Unified Risk Scoring Engine | **Critical** | The risk engine must combine model outputs into a composite score: $R = 100 \times (0.65P + 0.35A)$ and categorize scores into Low (0-29), Medium (30-59), High (60-79), and Critical (80-100). |
| **FR-09** | Automated Case Management | **Critical** | High and Critical risk transactions ($R \ge 60$) must automatically generate an `investigation_case` linked to the transaction, alert, and supporting evidence. |
| **FR-10** | Bedrock GenAI Investigation Assistant | **High** | The system must prompt Amazon Bedrock with verified transaction evidence to generate a structured case summary, bulleted factual evidence, and recommended actions without hallucinating fraud decisions. |
| **FR-11** | Interactive Investigator Dashboard | **High** | A React frontend must display live transaction feeds, alert queues, risk score distributions, Bedrock investigation reports, and case details. |
| **FR-12** | Immutable Audit Trail | **Critical** | Every state transition (case creation, assignment, investigator decision, notes, AI report generation) must be recorded in an immutable PostgreSQL `audit_logs` table. |
| **FR-13** | Secure REST APIs | **Critical** | A FastAPI service must expose versioned `/api/v1` endpoints protected by JWT authentication, role-based authorization (RBAC), and input validation schemas. |
| **FR-14** | Infrastructure as Code Deployment | **High** | All AWS resources (Kinesis, Lambda, S3, Glue, SageMaker, Bedrock IAM, RDS, ECS, CloudWatch) must be provisioned via modular Terraform templates across Dev, Staging, and Prod. |
| **FR-15** | CloudWatch Monitoring & Alerting | **High** | End-to-end telemetry must be captured via CloudWatch Metrics and Alarms, alerting operators on stream iterator age, Lambda errors, DLQ message counts, and API 5xx spikes. |

---

## 2. Detailed Functional Workflows

### FR-08 & FR-09: Risk Evaluation & Case Creation Logic
```
function evaluate_risk(P_xgboost, A_isoforest, transaction):
    risk_score = 100 * (0.65 * P_xgboost + 0.35 * A_isoforest)
    
    if risk_score >= 80.0:
        level = "CRITICAL"
        action = "FREEZE_AND_CREATE_CASE"
    elif risk_score >= 60.0:
        level = "HIGH"
        action = "CREATE_CASE"
    elif risk_score >= 30.0:
        level = "MEDIUM"
        action = "MONITOR"
    else:
        level = "LOW"
        action = "APPROVE"
        
    return risk_score, level, action
```

### FR-10: Bedrock GenAI Assistant Contract
- Input:
  - Current transaction details (amount, channel, merchant, timestamp).
  - Historical customer baseline (average transaction amount, common devices, frequent locations).
  - Engineered velocity features (count in last 5m, deviation ratio).
  - Model risk score breakdown.
- Output Specification (JSON):
  ```json
  {
    "summary": "String explaining the contextual reason for the alert",
    "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
    "key_evidence": [
      "Factual bullet 1 with numerical comparison",
      "Factual bullet 2"
    ],
    "recommended_actions": [
      "Suggested action 1 for investigator",
      "Suggested action 2"
    ]
  }
  ```
