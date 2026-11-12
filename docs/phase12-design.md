# Phase 12: Enterprise Incident Response, SOC, Automated Threat Investigation & Remediation

## 1. Architecture Overview

Phase 12 transforms FinGuard AI's multi-layered security alerts (CloudTrail, GuardDuty, Security Hub, and real-time fraud scoring) into an enterprise Security Operations Center (SOC) incident response platform with automated triage, evidence-grounded AI briefs, standardized playbooks, human approval gates, and verified remediation execution receipts.

```
+-----------------------------------------------------------------------------------+
|                            Security Event Ingestion                               |
|  - Amazon GuardDuty Finding Events (UnauthorizedAccess, Recon, Trojan)            |
|  - AWS Security Hub Findings (CIS Benchmark Violations)                           |
|  - FinGuard AI Real-Time Streaming Fraud Alerts (HighVelocityBurst, UPI Takeover) |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                 Event Normalization, Correlation & Deduplication                  |
|  - Fingerprint Generation (SHA-256 Resource + Event Hash)                         |
|  - Alert Correlation (Attaches Related Events to Active Cases within Window)      |
|  - Severity-Based SLA Target Assignment (Critical: 15m, High: 30m, Med: 120m)     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           SOC Incident Management Case                            |
|  - Ownership, Assignment, Status Transitions (NEW -> CONTAINED -> RESOLVED)       |
|  - Chronological Audit Timeline                                                   |
+-----------------------------------------+-----------------------------------------+
                                          |
         +--------------------------------+--------------------------------+
         |                                                                 |
         v                                                                 v
+----------------------------------+             +----------------------------------+
|      AI Investigation Brief      |             |     Response Playbook Engine     |
|  - Evidence-grounded synthesis   |             |  - Dry-Run Containment Plans     |
|  - Threat hypotheses formulation |             |  - Rollback Guidance Procedures  |
|  - Tactical SOC checks checklist |             |  - Mandatory Human Approval Gate |
+----------------------------------+             +-----------------+----------------+
                                                                   |
                                                                   v
                                                 +----------------------------------+
                                                 |   Separation of Duties Workflow  |
                                                 |  - Requester != Approver         |
                                                 |  - Controlled Sandbox Executor   |
                                                 |  - Verified Remediation Receipt  |
                                                 +----------------------------------+
```

---

## 2. Safety Governance Boundaries

To ensure regulatory banking safety and prevent autonomous disruption of production payment channels:
1. **Advisory AI Boundaries:** Generative AI compiles threat evidence, formulates hypotheses, and suggests checks; it is strictly prohibited from autonomously modifying infrastructure, revoking credentials, or isolating accounts.
2. **Separation of Duties:** The analyst who requests a containment action cannot approve their own action. Approval requires authorization by a distinct lead investigator or admin (`requested_by != approver`).
3. **Controlled Sandbox Execution:** Remediation actions are executed through an allowlisted executor producing verified `RemediationReceipt` artifacts with tamper-evident audit references.

---

## 3. Implemented Modules & Capabilities

| Module | Purpose | Location |
| :--- | :--- | :--- |
| **Event Normalization** | Converts GuardDuty, Security Hub, and Fraud alerts into `NormalizedSecurityEvent` | `soc/event_normalizer.py` |
| **Deduplication & Correlation** | Aggregates repeated alerts by resource fingerprint into active incidents | `soc/incident_store.py` |
| **SLA Management** | Severity-driven containment targets (Critical: 15m, High: 30m) | `soc/incident_store.py` |
| **AI Investigation** | Grounded brief, threat context, hypotheses, and recommended checks | `soc/ai_investigation.py` |
| **Playbook Engine** | Account compromise, S3 data exfiltration, and payment burst playbooks | `soc/playbooks.py` |
| **Approval Workflow** | Formal human approval gate enforcing separation of duties | `soc/remediation_executor.py` |
| **Controlled Remediation** | Allowlisted simulation executor generating audit receipts | `soc/remediation_executor.py` |
| **SOC API** | Endpoints for incident triage, approvals, execution, and metrics | `api/soc_router.py` |

---

## 4. SOC Lifecycle CLI Demonstration

Run the automated incident lifecycle demo:

```bash
python scripts/demo_incident.py --output artifacts/phase12
```

Outputs:
- `artifacts/phase12/incident_lifecycle_report.json`: Complete incident dossier with correlated events, timeline, approvals, and execution receipt.
- `artifacts/phase12/incident_summary.md`: Markdown report for executive SOC review.
