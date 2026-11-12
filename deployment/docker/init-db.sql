-- FinGuard AI PostgreSQL Initialization Script
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert Default System Roles
INSERT INTO roles (id, name, description) VALUES
('ADMIN', 'Platform Administrator', 'Full platform administrative and security access'),
('FRAUD_ANALYST', 'Fraud Analyst', 'Triage real-time alerts and initiate investigations'),
('INVESTIGATOR', 'Senior Investigator', 'Manage assigned cases and execute human determinations'),
('AUDITOR', 'Compliance Auditor', 'Read-only access to immutable audit trails and models'),
('DATA_ENGINEER', 'Data Engineer', 'Manage Glue pipelines, Athena queries, and schemas'),
('ML_ENGINEER', 'ML Engineer', 'Manage model training, evaluations, and SageMaker registries')
ON CONFLICT (id) DO NOTHING;
