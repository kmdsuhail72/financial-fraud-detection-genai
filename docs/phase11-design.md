# Phase 11: Enterprise Audit, Compliance, Risk Management and Security Monitoring

## 1. Architecture Overview

Phase 11 extends FinGuard AI with an automated, centralized compliance governance and risk monitoring architecture that ties together multi-region AWS security telemetry, immutable log archival, reference control frameworks (SOC 2 Type II and ISO/IEC 27001:2022), and real-time security posture assessment.

```
                    ┌──────────────────────────────────────────────┐
                    │  AWS Security & Cloud Governance Telemetry   │
                    │  - Multi-Region CloudTrail (ap-south-1 +)    │
                    │  - AWS Config Resource Compliance Recorders  │
                    │  - Amazon GuardDuty Threat Detection         │
                    │  - AWS Security Hub Standard Benchmarks      │
                    └──────────────────────┬───────────────────────┘
                                           │
                         Encrypted S3 & CloudWatch Logs
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │      Centralized Security Audit Layer        │
                    │  - S3 Audit Bucket (KMS CMK + Object Lock)   │
                    │  - Customer Managed Key (CMK) Auto-Rotation  │
                    │  - CloudWatch Alarms & SNS Security Topic    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │   Compliance Posture Engine & Collector      │
                    │  - Regulatory Control Mapping Dictionary     │
                    │  - Automated Evidence Ingestion & Scoring    │
                    │  - Audit Report Packaging & Markdown Export  │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     RBAC Protected Compliance Endpoints      │
                    │  - GET  /compliance/posture                  │
                    │  - GET  /compliance/controls                 │
                    │  - GET  /compliance/findings                 │
                    │  - POST /compliance/evidence/collect         │
                    └──────────────────────────────────────────────┘
```

---

## 2. Regulatory Reference Control Mappings

The compliance dictionary maps SOC 2 Type II (Trust Services Criteria) and ISO/IEC 27001:2022 controls to FinGuard AI architectural evidence:

| Framework | Control ID | Title | FinGuard AI Architecture Mapping | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **SOC 2** | `CC6.1` | Logical Access Controls & MFA | Amazon Cognito User Pool + JWT signature verification + RBAC | `EVID-COGNITO-CONFIG` |
| **SOC 2** | `CC6.6` | Boundary Protection & TLS | AWS WAF, VPC security groups, TLS 1.3 encryption in transit | `EVID-TLS-POLICY` |
| **SOC 2** | `CC6.8` | Change Management & IaC | Terraform version-controlled IaC and GitHub Actions CI pipelines | `EVID-TERRAFORM-PLAN` |
| **SOC 2** | `CC7.1` | Threat Detection & Vulnerabilities | Amazon GuardDuty runtime/S3 detection and AWS Security Hub | `EVID-GUARDDUTY-STATUS` |
| **SOC 2** | `CC7.2` | Event Monitoring & Incident Alarms | Multi-region CloudTrail, CloudWatch alarms, and SNS security alerts | `EVID-CLOUDTRAIL-LOGS` |
| **ISO 27001** | `A.5.15` | Access Control & Least Privilege | Principle of least privilege IAM roles and scoped Cognito permissions | `EVID-IAM-POLICIES` |
| **ISO 27001** | `A.8.7` | Protection Against Malware | GuardDuty automated malware protection for inbound S3 objects | `EVID-GUARDDUTY-STATUS` |
| **ISO 27001** | `A.8.12`| Data Leakage Prevention | Multi-tier S3 data lake isolation with KMS CMK encryption at rest | `EVID-S3-ENCRYPTION` |
| **ISO 27001** | `A.8.16`| Monitoring Activities | Immutable point-in-time DynamoDB audit logs and CloudTrail validation | `EVID-AUDIT-TABLE` |
| **ISO 27001** | `A.8.24`| Cryptographic Controls & Key Governance | AWS KMS Customer Managed Keys (CMK) with annual automatic rotation | `EVID-KMS-ROTATION` |

> [!NOTE]
> Control mappings serve as automated compliance evidence management aids for enterprise audit preparation; they do not constitute independent third-party certification.

---

## 3. Automated Evidence Collection CLI & Reports

Run automated evidence ingestion from any security telemetry snapshot:

```bash
python scripts/collect_evidence.py \
  --input examples/sample_security_snapshot.json \
  --output artifacts/phase11
```

Generated audit artifacts:
1. `artifacts/phase11/compliance_report.json`: Machine-readable compliance report containing posture summary, control statuses, and active findings.
2. `artifacts/phase11/compliance_summary.md`: Human-readable executive summary table for audit and governance officers.

---

## 4. Protected Compliance API Endpoints

All compliance routes require authenticated identity with `audit:view` permission (granted to **Auditor** and **Admin** roles; unauthorized roles receive `403 Forbidden`):

- `GET /compliance/posture`: Overall framework scores, compliance percentage, open findings count.
- `GET /compliance/controls`: Regulatory control catalogue with status and mapped services.
- `GET /compliance/findings`: Active security findings with severity, affected resources, and remediation guidance.
- `POST /compliance/evidence/collect`: Triggers an automated compliance evaluation cycle.
