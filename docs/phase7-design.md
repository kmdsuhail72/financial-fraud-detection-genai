# FinGuard AI — Phase 7: Real-Time Fraud Scoring & SageMaker Deployment

## 1. Executive Summary

Phase 7 connects the machine learning models trained in Phase 6 to the live transaction stream established in Phase 3. Incoming financial transactions from Amazon Kinesis are decoded, validated, scored by the Amazon SageMaker endpoint, evaluated by the Risk Decision Engine, stored with idempotency in Amazon DynamoDB, and conditionally escalated to an Amazon SQS investigation queue when high risk is detected.

---

## 2. End-to-End Architecture

```
+─────────────────────────────────────────────────────────────────────────────────────────+
|                           Phase 7 Real-Time Scoring Pipeline                            |
+─────────────────────────────────────────────────────────────────────────────────────────+
|                                                                                         |
|   Amazon Kinesis Data Streams (Phase 3 Stream)                                          |
|        │                                                                                |
|        ▼ (Batch Polling via ESM with ReportBatchItemFailures)                           |
|   AWS Lambda: Fraud Scoring Consumer (lambda_scoring/handler.py)                        |
|        │                                                                                |
|        ├─ 1. Base64 Decode & Schema Validation                                          |
|        │                                                                                |
|        ├─ 2. Feature Extraction & Normalization                                         |
|        │                                                                                |
|        ├─ 3. Amazon SageMaker Endpoint (Random Forest / XGBoost + Isolation Forest)     |
|        │     Returns: P(Fraud) in [0.0, 1.0], Anomaly Score A in [0.0, 1.0]             |
|        │                                                                                |
|        ├─ 4. Risk Decision Engine                                                       |
|        │     Combined Risk Score: R = 0.65 * P + 0.35 * A                               |
|        │     Tier Categorization:                                                       |
|        │       - R >= 0.60: HIGH (Action: INVESTIGATE, Dispatches SQS Alert)            |
|        │       - R >= 0.35: REVIEW (Action: REVIEW, Logged for Monitoring)              |
|        │       - R <  0.35: LOW (Action: ALLOW, Normal Transaction)                     |
|        │                                                                                |
|        ├─ 5. Amazon DynamoDB (finguard-fraud-decisions)                                 |
|        │     Conditional Write: attribute_not_exists(transaction_id)                    |
|        │     Guarantees Idempotency & Stores Decision Audit Record                      |
|        │                                                                                |
|        ├─ 6. Amazon SQS (finguard-investigation-alerts)                                 |
|        │     Receives HIGH risk investigation cases for Phase 8 Bedrock Assistant       |
|        │                                                                                |
|        └─ 7. Amazon CloudWatch                                                          |
|              Metric Alarms: Lambda Errors (> 5), Concurrency Throttles (> 1)            |
|                                                                                         |
+─────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Core Components

### 3.1 Model Packaging (`scripts/phase7/package_model.py`)
Generates the SageMaker model artifact `artifacts/sagemaker/model.tar.gz` conforming to AWS SageMaker Scikit-learn container conventions:
```
model.tar.gz
├── model.joblib
└── code/
    └── inference.py
```

### 3.2 SageMaker Real-Time Inference (`sagemaker/inference.py`)
Implements the standard SageMaker container hooks:
- `model_fn(model_dir)`: Loads `model.joblib`.
- `input_fn(request_body, content_type)`: Decodes JSON payload.
- `predict_fn(input_data, model)`: Computes supervised fraud probability and unsupervised anomaly score.
- `output_fn(prediction, accept)`: Formats prediction into JSON.

### 3.3 Risk Decision Engine (`lambda_scoring/risk_engine.py`)
Computes combined risk score $R$:
$$R = 0.65 \cdot P(\text{fraud}) + 0.35 \cdot A(\text{anomaly})$$

| Risk Level | Score Cutoff | Decision Action | Downstream Workflow |
| :--- | :--- | :--- | :--- |
| **LOW** | $R < 0.35$ | `ALLOW` | Transaction proceeds without friction. |
| **REVIEW** | $0.35 \le R < 0.60$ | `REVIEW` | Stepped-up auth or analyst monitoring. |
| **HIGH** | $R \ge 0.60$ | `INVESTIGATE` | Alert dispatched to SQS; case queued for Phase 8. |

> [!IMPORTANT]
> A `HIGH` risk result is an investigation signal, not an irreversible account termination. Actual ledger debits and cardholder notifications follow approved compliance and governance policies.

### 3.4 DynamoDB Idempotency & Decisions (`lambda_scoring/dynamodb_decisions.py`)
Stores every scored transaction in `finguard-fraud-decisions`:
- **Partition Key:** `transaction_id` (String)
- **Global Secondary Index:** `RiskLevelIndex` (`risk_level` PK, `decision_timestamp` SK)
- **Conditional Write:** `attribute_not_exists(transaction_id)` to suppress duplicate processing from streaming retries.
- **TTL:** 90 days automatic record expiration.

### 3.5 SQS Investigation Alerts (`lambda_scoring/sqs_alerts.py`)
Dispatches structured alert events to `finguard-investigation-alerts` with 14-day retention and a Dead-Letter Queue (DLQ) after 3 receive attempts.

---

## 4. Terraform Infrastructure (`infrastructure/terraform/phase7/`)

The infrastructure is provisioned in `ap-south-1` (Mumbai):
- **DynamoDB:** `finguard-fraud-decisions-dev` with on-demand capacity and point-in-time recovery.
- **SQS:** `finguard-investigation-alerts-dev` and DLQ.
- **SageMaker Model:** `finguard-fraud-model-dev` referencing S3 `model.tar.gz`.
- **SageMaker Endpoint:** Conditional on `enable_sagemaker_endpoint` (default `false` to avoid hourly EC2 idle charges).
- **Lambda:** `finguard-fraud-scoring-consumer-dev` with least-privilege IAM and Kinesis Event Source Mapping (`ReportBatchItemFailures`).
- **CloudWatch Alarms:** Alarms on Lambda errors and throttling.

To initialize and validate:
```bash
cd infrastructure/terraform/phase7
terraform init
terraform validate
```

