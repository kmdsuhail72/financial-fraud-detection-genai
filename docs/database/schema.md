# FinGuard AI — Relational Database Schema Specification

## 1. Database Overview
FinGuard AI uses **PostgreSQL 15+** for transactional integrity, operational state management, and auditability.
- Primary Keys use UUIDv4 to eliminate sequence collisions in distributed environments.
- Foreign keys maintain referential integrity with cascading or restrict rules.
- Indexes optimize high-frequency lookups (e.g., `account_id`, `transaction_timestamp`, `risk_score`, `case_status`).

---

## 2. Table Definitions

### 1. `roles`
Access control definitions.
```sql
CREATE TABLE roles (
    id VARCHAR(50) PRIMARY KEY, -- e.g., 'ADMIN', 'INVESTIGATOR', 'FRAUD_ANALYST', 'AUDITOR'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

### 2. `users`
System operators and investigators.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id VARCHAR(50) REFERENCES roles(id) ON DELETE RESTRICT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_users_role_id ON users(role_id);
```

### 3. `customers`
Synthetic customer banking profiles.
```sql
CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY, -- e.g., 'CUS-200045'
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    risk_segment VARCHAR(50) DEFAULT 'STANDARD', -- 'LOW', 'STANDARD', 'HIGH_NET_WORTH'
    kyc_status VARCHAR(50) DEFAULT 'VERIFIED',
    country VARCHAR(10) DEFAULT 'IN',
    city VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

### 4. `accounts`
Bank account records linked to customers.
```sql
CREATE TABLE accounts (
    id VARCHAR(50) PRIMARY KEY, -- e.g., 'ACC-100045'
    customer_id VARCHAR(50) REFERENCES customers(id) ON DELETE CASCADE,
    account_type VARCHAR(50) NOT NULL, -- 'SAVINGS', 'CURRENT', 'CREDIT_CARD'
    balance NUMERIC(15, 2) DEFAULT 0.00 NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR' NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL, -- 'ACTIVE', 'FROZEN', 'CLOSED'
    opened_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
```

### 5. `transactions`
Raw transaction events.
```sql
CREATE TABLE transactions (
    id VARCHAR(64) PRIMARY KEY, -- e.g., 'TXN-20261112-000001'
    account_id VARCHAR(50) REFERENCES accounts(id) ON DELETE RESTRICT,
    customer_id VARCHAR(50) REFERENCES customers(id) ON DELETE RESTRICT,
    transaction_type VARCHAR(50) NOT NULL, -- 'CARD_PAYMENT', 'UPI_TRANSFER', 'ATM_WITHDRAWAL', 'WIRE'
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR' NOT NULL,
    merchant_id VARCHAR(100),
    merchant_category VARCHAR(100),
    channel VARCHAR(50) NOT NULL, -- 'MOBILE', 'WEB', 'POS', 'ATM'
    location_country VARCHAR(10),
    location_city VARCHAR(100),
    device_id VARCHAR(100),
    ip_address VARCHAR(45),
    is_international BOOLEAN DEFAULT FALSE NOT NULL,
    transaction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL, -- 'PENDING', 'APPROVED', 'DECLINED', 'HELD'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_timestamp ON transactions(transaction_timestamp DESC);
```

### 6. `fraud_predictions`
Machine learning scoring inference records.
```sql
CREATE TABLE fraud_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(64) UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
    model_version VARCHAR(50) NOT NULL,
    xgboost_prob NUMERIC(6, 4) NOT NULL, -- 0.0000 to 1.0000
    isoforest_score NUMERIC(6, 4) NOT NULL, -- 0.0000 to 1.0000
    unified_risk_score NUMERIC(5, 2) NOT NULL, -- 0.00 to 100.00
    risk_level VARCHAR(20) NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    feature_snapshot JSONB NOT NULL, -- Serialized velocity features
    inference_latency_ms NUMERIC(8, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_fraud_pred_score ON fraud_predictions(unified_risk_score DESC);
CREATE INDEX idx_fraud_pred_level ON fraud_predictions(risk_level);
```

### 7. `fraud_alerts`
Generated alerts for medium, high, and critical risk items.
```sql
CREATE TABLE fraud_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(64) REFERENCES transactions(id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 2) NOT NULL,
    alert_level VARCHAR(20) NOT NULL, -- 'MEDIUM', 'HIGH', 'CRITICAL'
    alert_reason TEXT NOT NULL,
    is_acknowledged BOOLEAN DEFAULT FALSE NOT NULL,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_alerts_level ON fraud_alerts(alert_level);
CREATE INDEX idx_alerts_acknowledged ON fraud_alerts(is_acknowledged);
```

### 8. `investigation_cases`
Investigator workflow container for high/critical transactions.
```sql
CREATE TABLE investigation_cases (
    id VARCHAR(64) PRIMARY KEY, -- e.g., 'CASE-20261112-00001'
    transaction_id VARCHAR(64) UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN' NOT NULL, -- 'OPEN', 'IN_REVIEW', 'ESCALATED', 'CLOSED'
    priority VARCHAR(20) DEFAULT 'HIGH' NOT NULL, -- 'NORMAL', 'HIGH', 'URGENT'
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_cases_status ON investigation_cases(status);
CREATE INDEX idx_cases_assigned ON investigation_cases(assigned_to);
CREATE INDEX idx_cases_risk ON investigation_cases(risk_score DESC);
```

### 9. `investigation_evidence`
Discrete evidence items linked to a case.
```sql
CREATE TABLE investigation_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(64) REFERENCES investigation_cases(id) ON DELETE CASCADE,
    evidence_type VARCHAR(100) NOT NULL, -- 'VELOCITY_SPIKE', 'NEW_DEVICE', 'LOCATION_MISMATCH', 'HIGH_AMOUNT'
    description TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'RULE_ENGINE' NOT NULL, -- 'ML_FEATURE', 'RULE_ENGINE', 'EXTERNAL_THREAT'
    confidence_score NUMERIC(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_evidence_case ON investigation_evidence(case_id);
```

### 10. `ai_investigation_reports`
Bedrock GenAI generated summaries and recommendations.
```sql
CREATE TABLE ai_investigation_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(64) REFERENCES investigation_cases(id) ON DELETE CASCADE,
    bedrock_model_id VARCHAR(100) NOT NULL,
    executive_summary TEXT NOT NULL,
    extracted_evidence JSONB NOT NULL, -- Array of grounded evidence strings
    recommended_actions JSONB NOT NULL, -- Array of recommended actions
    prompt_tokens INT,
    completion_tokens INT,
    generation_latency_ms NUMERIC(8, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_ai_reports_case ON ai_investigation_reports(case_id);
```

### 11. `investigator_decisions`
Human decisions and resolution actions.
```sql
CREATE TABLE investigator_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(64) REFERENCES investigation_cases(id) ON DELETE CASCADE,
    investigator_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    decision VARCHAR(50) NOT NULL, -- 'CONFIRMED_FRAUD', 'FALSE_POSITIVE', 'SUSPICIOUS_MONITOR'
    action_taken VARCHAR(100) NOT NULL, -- 'ACCOUNT_FROZEN', 'TRANSACTION_REVERSED', 'CLEARED', 'SAR_FILED'
    notes TEXT NOT NULL,
    decision_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_decisions_case ON investigator_decisions(case_id);
CREATE INDEX idx_decisions_user ON investigator_decisions(investigator_id);
```

### 12. `audit_logs`
Immutable audit log of all system transitions and user actions.
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(100) NOT NULL, -- 'case', 'transaction', 'alert', 'user'
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL, -- 'CREATE', 'UPDATE', 'ASSIGN', 'DECIDE', 'AI_SUMMARY'
    performed_by UUID REFERENCES users(id),
    previous_state JSONB,
    new_state JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_audit_entity ON audit_logs(entity_name, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
```

### 13. `model_registry`
Model metadata and performance tracking.
```sql
CREATE TABLE model_registry (
    id VARCHAR(100) PRIMARY KEY, -- e.g., 'xgboost-v1.0.0'
    model_type VARCHAR(50) NOT NULL, -- 'XGBOOST', 'ISOLATION_FOREST', 'RANDOM_FOREST'
    s3_artifact_uri VARCHAR(255) NOT NULL,
    metrics JSONB NOT NULL, -- Precision, Recall, AUC, PR-AUC
    hyperparameters JSONB,
    is_active BOOLEAN DEFAULT FALSE NOT NULL,
    trained_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deployed_at TIMESTAMP WITH TIME ZONE
);
```

