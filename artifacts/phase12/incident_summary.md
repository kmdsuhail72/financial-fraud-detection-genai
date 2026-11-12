# SOC Incident Investigation & Containment Report

- **Incident ID:** `INC-20261112-C21E`
- **Severity:** **MEDIUM**
- **Status:** `CONTAINED`
- **Primary Resource:** `arn:aws:::generic-resource`
- **SLA Target:** 120 mins (Compliant)

## AI Investigation Brief

SOC Alert INC-20261112-C21E (MEDIUM) originated from InternalSecurity targeting arn:aws:::generic-resource. Observed pattern indicates potential unauthorized activity with 1 correlated alert(s).

### Recommended Checks
- Query CloudTrail for all API actions initiated by the actor associated with arn:aws:::generic-resource in the last 2 hours.
- Verify whether a corresponding Jira change ticket exists for this resource activity.
- Inspect source IP reputation against external threat intelligence feeds.
- Review proposed containment playbook actions prior to executing remediation.

## Containment Actions Executed

- Action: `Block Adversary Remote IP Address`
- Approved By: `soc-lead@finguard.internal`
- Receipt: `RCPT-45A3738F` (SIMULATED_SUCCESS)

## Audit Timeline (5 entries)

| Timestamp | Author | Action | Description |
| :--- | :--- | :--- | :--- |
| 2026-11-12T19:45:46.071555+00:00 | `SOCEngine` | CREATION | Incident case initialized from InternalSecurity event EVT-13916967. |
| 2026-11-12T19:45:46.072048+00:00 | `AIAssistant` | AI_INVESTIGATION | Grounded AI threat synthesis and hypothesis checks compiled. |
| 2026-11-12T19:45:46.072148+00:00 | `analyst@finguard.internal` | APPROVAL_REQUESTED | Remediation approval requested for action ACT-BLOCK-ADVERSARY-IP. |
| 2026-11-12T19:45:46.072219+00:00 | `soc-lead@finguard.internal` | APPROVAL_APPROVED | Remediation action ACT-BLOCK-ADVERSARY-IP was APPROVED by soc-lead@finguard.internal. |
| 2026-11-12T19:45:46.072335+00:00 | `soc-lead@finguard.internal` | REMEDIATION_EXECUTED | Simulated containment action 'Block Adversary Remote IP Address' executed on arn:aws:::generic-resource. |
