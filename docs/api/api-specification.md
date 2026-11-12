# FinGuard AI — REST API Specification (v1)

## 1. Overview & General Standards
- **Base URL:** `https://api.finguard.internal/api/v1` (or `http://localhost:8000/api/v1` for local development)
- **Protocol:** HTTPS / TLS 1.3
- **Authentication:** Bearer JWT in the `Authorization` header (`Bearer <token>`)
- **Content-Type:** `application/json`
- **Error Response Format:**
  ```json
  {
    "error_code": "RESOURCE_NOT_FOUND",
    "message": "Transaction TXN-20261112-999999 was not found.",
    "timestamp": "2026-11-12T10:30:00Z",
    "details": {}
  }
  ```

---

## 2. API Endpoints Catalog

| Method | Endpoint | Description | Required Role |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/transactions` | Ingests a new transaction event | System / API Gateway |
| `GET` | `/api/v1/transactions` | Lists paginated transactions | Fraud Analyst, Investigator |
| `GET` | `/api/v1/transactions/{id}` | Retrieves specific transaction detail | Fraud Analyst, Investigator |
| `GET` | `/api/v1/fraud/alerts` | Lists open and acknowledged alerts | Fraud Analyst, Investigator |
| `GET` | `/api/v1/fraud/alerts/{id}` | Retrieves alert detail with model scores | Fraud Analyst, Investigator |
| `POST` | `/api/v1/fraud/score` | Synchronously scores a transaction vector | System / ML Pipeline |
| `GET` | `/api/v1/cases` | Lists paginated investigation cases | Investigator, Admin |
| `GET` | `/api/v1/cases/{id}` | Full case dossier (features, evidence, AI) | Investigator, Admin |
| `POST` | `/api/v1/cases/{id}/assign` | Assigns an investigator to a case | Investigator, Admin |
| `POST` | `/api/v1/cases/{id}/decision` | Records human decision (Fraud/False Pos) | Investigator |
| `POST` | `/api/v1/cases/{id}/investigate` | Triggers Amazon Bedrock AI summary | Investigator, Fraud Analyst |
| `GET` | `/api/v1/dashboard/summary` | Triage statistics and KPI counters | All authenticated roles |
| `GET` | `/api/v1/audit-logs` | Immutable audit trail query | Auditor, Admin |

---

## 3. Detailed Endpoint Contracts

### 3.1 `POST /api/v1/transactions`
Submits a transaction into the streaming ingestion pipeline.

**Request Payload:**
```json
{
  "transaction_id": "TXN-20261112-000001",
  "account_id": "ACC-100045",
  "customer_id": "CUS-200045",
  "transaction_type": "CARD_PAYMENT",
  "amount": 87500.00,
  "currency": "INR",
  "merchant_id": "MER-90012",
  "merchant_category": "ELECTRONICS",
  "transaction_timestamp": "2026-11-12T10:30:00Z",
  "channel": "MOBILE",
  "location": {
    "country": "IN",
    "city": "Kolkata"
  },
  "device_id": "DEV-45002",
  "ip_address": "192.0.2.10",
  "is_international": false
}
```

**Response (202 Accepted):**
```json
{
  "status": "ACCEPTED",
  "transaction_id": "TXN-20261112-000001",
  "stream_sequence_number": "496352849182390123849182",
  "timestamp": "2026-11-12T10:30:00.124Z"
}
```

---

### 3.2 `POST /api/v1/fraud/score`
Computes real-time risk scores using the dual-model engine.

**Request Payload:**
```json
{
  "transaction_id": "TXN-20261112-000001",
  "amount": 87500.00,
  "avg_amount_24h": 12500.00,
  "transaction_count_5m": 4,
  "transaction_count_1h": 7,
  "amount_deviation": 7.0,
  "new_device": true,
  "location_change": false,
  "is_international": false,
  "merchant_risk": 0.42,
  "account_age_days": 180
}
```

**Response (200 OK):**
```json
{
  "transaction_id": "TXN-20261112-000001",
  "xgboost_probability": 0.9250,
  "isoforest_anomaly_score": 0.8800,
  "unified_risk_score": 90.93,
  "risk_level": "CRITICAL",
  "recommended_action": "FREEZE_AND_CREATE_CASE",
  "latency_ms": 38.5
}
```

---

### 3.3 `POST /api/v1/cases/{id}/investigate`
Prompts Amazon Bedrock to synthesize evidence into an investigator summary.

**Response (200 OK):**
```json
{
  "case_id": "CASE-20261112-00001",
  "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
  "executive_summary": "The transaction has been flagged as CRITICAL risk because its amount (₹87,500) is 7.0x the customer's 24-hour baseline (₹12,500), combined with a rapid succession of 4 transactions in 5 minutes from an unrecognized mobile device.",
  "key_evidence": [
    "Transaction amount (₹87,500) exceeds average 24h baseline by 7.0x",
    "Unrecognized device DEV-45002 observed for the first time",
    "High velocity burst: 4 transactions initiated within 5 minutes",
    "Electronics merchant category with elevated historical dispute rates"
  ],
  "recommended_actions": [
    "Verify customer presence via outbound challenge on registered phone",
    "Place temporary freeze on account ACC-100045 pending confirmation",
    "Review correlated IP 192.0.2.10 against threat intelligence feeds"
  ],
  "generation_latency_ms": 1420.0
}
```

---

### 3.4 `POST /api/v1/cases/{id}/decision`
Records a human investigator's adjudication and triggers case closure.

**Request Payload:**
```json
{
  "decision": "CONFIRMED_FRAUD",
  "action_taken": "ACCOUNT_FROZEN",
  "notes": "Spoke to customer; confirmed card compromised via phishing. Card deactivated and refund initiated."
}
```

**Response (200 OK):**
```json
{
  "decision_id": "8d6b8b0e-6277-4f6c-9411-cfb159f47e22",
  "case_id": "CASE-20261112-00001",
  "status": "CLOSED",
  "adjudicated_by": "f083d9bc-c15a-4cb7-a54b-d2424cf37c38",
  "timestamp": "2026-11-12T10:45:00Z"
}
```
