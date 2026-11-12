# FinGuard AI — Phase 8: Fraud Investigation Management & Amazon Bedrock GenAI Assistant

## 1. Executive Summary

Phase 8 builds the analyst-facing investigation platform on top of the real-time scoring pipeline from Phase 7. When a transaction receives a `REVIEW` or `HIGH` risk classification, an investigation case is automatically generated. Amazon Bedrock synthesizes an evidence-grounded investigation summary, explains anomalous risk features, presents alternative benign hypotheses, and suggests investigative standard operating procedures (SOPs).

---

## 2. Ethical AI Governance & Separation of Responsibilities

A strict separation of concerns is maintained across the automated systems and human operators:

| Layer | Responsibility | Authority Boundaries |
| :--- | :--- | :--- |
| **ML Engine (Phase 6)** | Estimates statistical risk $P(\text{fraud})$ and anomaly score $A$. | **No legal authority.** Produces risk scores only. |
| **Bedrock Assistant (Phase 8)** | Synthesizes evidence, highlights metrics, suggests checks. | **No decision authority.** Cannot declare guilt, freeze accounts, or decline payments. |
| **Accredited Human Analyst** | Reviews evidence, interviews cardholders, adjudicates cases. | **Sole decision authority.** Executes binding financial and account actions. |

---

## 3. End-to-End Architecture

```
+─────────────────────────────────────────────────────────────────────────────────────────+
|                        Phase 8 Fraud Investigation Platform                             |
+─────────────────────────────────────────────────────────────────────────────────────────+
|                                                                                         |
|   Phase 7 SQS Alert: finguard-investigation-alerts                                      |
|        │                                                                                |
|        ▼ (Batch Polling via ESM with ReportBatchItemFailures)                           |
|   AWS Lambda: Case Orchestrator (lambda_case_orchestrator/handler.py)                    |
|        │                                                                                |
|        ├─ 1. Idempotency Check & Transaction Deduplication                             |
|        │     Queries DynamoDB by transaction_id to prevent duplicate cases              |
|        │                                                                                |
|        ├─ 2. Evidence Collection                                                        |
|        │     Aggregates transaction features, baseline average, and velocity            |
|        │                                                                                |
|        ├─ 3. Amazon Bedrock Converse API (Claude 3.5 Sonnet / Haiku)                    |
|        │     - Executive Summary grounded in quantitative comparisons                   |
|        │     - Key Evidence breakdown                                                   |
|        │     - Alternative benign explanations                                          |
|        │     - Suggested investigative action steps                                     |
|        │                                                                                |
|        └─ 4. Amazon DynamoDB: finguard-investigation-cases                              |
|              Persists case, evidence, AI summary, notes, and audit trail                |
|                                                                                         |
|   FastAPI Investigation Management API (Port 8001 / api/app.py)                        |
|        │                                                                                |
|        ├─ GET   /health              (Health check & store readiness)                   |
|        ├─ GET   /cases               (List cases with status/priority filtering)        |
|        ├─ GET   /cases/{case_id}     (Retrieve case details, notes & audit trail)       |
|        └─ PATCH /cases/{case_id}     (Update status, assign analyst & add notes)        |
|                                                                                         |
+─────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 4. Investigation Case State Machine

```
              ┌───────────────┐
              │     OPEN      │ (Case created automatically from SQS alert)
              └───────┬───────┘
                      │
                      │ Assigned to Analyst / In Progress
                      ▼
              ┌───────────────┐
              │   IN_REVIEW   │ (Analyst adds notes, checks devices, verifies OTP)
              └───────┬───────┘
                      │
       ┌──────────────┴──────────────┐
       │ Escalated to Senior Team    │ Adjudicated by Investigator
       ▼                             ▼
┌───────────────┐             ┌───────────────┐
│   ESCALATED   │             │   RESOLVED    │
└───────┬───────┘             └───────┬───────┘
        │                             │
        └─────────────────────────────┤ (Case finalized & locked)
                                      ▼
                              ┌───────────────┐
                              │    CLOSED     │
                              └───────────────┘
```

---

## 5. Case Resolution Actions

When resolving a case via `PATCH /cases/{case_id}`, investigators select one of the following compliance actions:
- `CONFIRMED_FRAUD`: Fraud pattern confirmed; chargeback initiated.
- `FALSE_POSITIVE`: Benign customer behavior verified; feedback routed for model retraining.
- `ACCOUNT_RESTRICTED`: Protective hold applied to prevent further unauthorized drain.
- `STEP_UP_VERIFIED`: Customer successfully verified transaction via two-factor challenge.
- `DISMISSED`: Low-impact anomaly determined to be non-actionable.

---

## 6. Running the Investigation API Locally

```powershell
uvicorn api.app:app --host 0.0.0.0 --port 8001
```

### Sample Analyst Update Request
```bash
curl -X PATCH http://localhost:8001/cases/CASE-123 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_REVIEW",
    "assigned_to": "analyst@example.com",
    "note": "Reviewing device and transaction velocity patterns."
  }'
```

---

## 7. Terraform Infrastructure (`infrastructure/terraform/phase8/`)

Provisioned in `ap-south-1` (Mumbai):
- **DynamoDB:** `finguard-investigation-cases-dev` with GSIs `StatusIndex` (`status`, `created_at`) and `TransactionIndex` (`transaction_id`).
- **Lambda:** `finguard-case-orchestrator-dev` connected to `finguard-investigation-alerts` SQS queue.
- **IAM Policies:** Least-privilege access for Bedrock Converse (`bedrock:InvokeModel`, `bedrock:Converse`), DynamoDB, and SQS.

