# FinGuard AI — Entity-Relationship (ER) Diagram

## 1. Relational Architecture Diagram

```mermaid
erDiagram
    ROLES ||--o{ USERS : assigned_to
    CUSTOMERS ||--o{ ACCOUNTS : owns
    CUSTOMERS ||--o{ TRANSACTIONS : initiates
    ACCOUNTS ||--o{ TRANSACTIONS : executes
    
    TRANSACTIONS ||--o| FRAUD_PREDICTIONS : scored_by
    TRANSACTIONS ||--o{ FRAUD_ALERTS : triggers
    TRANSACTIONS ||--o| INVESTIGATION_CASES : creates
    
    USERS ||--o{ INVESTIGATION_CASES : assigned_to
    INVESTIGATION_CASES ||--o{ INVESTIGATION_EVIDENCE : contains
    INVESTIGATION_CASES ||--o| AI_INVESTIGATION_REPORTS : generates
    INVESTIGATION_CASES ||--o{ INVESTIGATOR_DECISIONS : resolves
    USERS ||--o{ INVESTIGATOR_DECISIONS : decides
    USERS ||--o{ AUDIT_LOGS : records_action
    
    ROLES {
        string id PK
        string name
        string description
    }

    USERS {
        uuid id PK
        string username
        string email
        string password_hash
        string role_id FK
        boolean is_active
    }

    CUSTOMERS {
        string id PK
        string first_name
        string last_name
        string risk_segment
        string kyc_status
    }

    ACCOUNTS {
        string id PK
        string customer_id FK
        string account_type
        numeric balance
        string status
    }

    TRANSACTIONS {
        string id PK
        string account_id FK
        string customer_id FK
        string transaction_type
        numeric amount
        string channel
        string status
        timestamp transaction_timestamp
    }

    FRAUD_PREDICTIONS {
        uuid id PK
        string transaction_id FK
        numeric xgboost_prob
        numeric isoforest_score
        numeric unified_risk_score
        string risk_level
        jsonb feature_snapshot
    }

    FRAUD_ALERTS {
        uuid id PK
        string transaction_id FK
        numeric risk_score
        string alert_level
        string alert_reason
        boolean is_acknowledged
    }

    INVESTIGATION_CASES {
        string id PK
        string transaction_id FK
        numeric risk_score
        string risk_level
        string status
        string priority
        uuid assigned_to FK
    }

    INVESTIGATION_EVIDENCE {
        uuid id PK
        string case_id FK
        string evidence_type
        string description
        string source
        numeric confidence_score
    }

    AI_INVESTIGATION_REPORTS {
        uuid id PK
        string case_id FK
        string bedrock_model_id
        text executive_summary
        jsonb extracted_evidence
        jsonb recommended_actions
    }

    INVESTIGATOR_DECISIONS {
        uuid id PK
        string case_id FK
        uuid investigator_id FK
        string decision
        string action_taken
        text notes
    }

    AUDIT_LOGS {
        uuid id PK
        string entity_name
        string entity_id
        string action
        uuid performed_by FK
        jsonb previous_state
        jsonb new_state
        timestamp timestamp
    }

    MODEL_REGISTRY {
        string id PK
        string model_type
        string s3_artifact_uri
        jsonb metrics
        boolean is_active
    }
```

---

## 2. Referential Integrity & Cascade Semantics
- **`accounts` -> `customers`:** Cascade delete on customer removal in test environments.
- **`transactions` -> `accounts`:** Restrict delete to prevent orphan financial records.
- **`investigation_cases` -> `transactions`:** 1-to-1 relationship enforced via unique constraint.
- **`investigator_decisions` -> `investigation_cases`:** Append-only history preserving multi-tier reviews.
- **`audit_logs`:** No cascade deletion; append-only compliance structure.

