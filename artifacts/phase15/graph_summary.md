# FinGuard AI — Enterprise Graph Analytics & Fraud Ring Detection

**Execution Timestamp:** {
  "total_nodes": 29,
  "total_edges": 35,
  "total_fraud_rings": 1,
  "total_circular_loops": 1
}

## 1. Discovered Fraud Rings

| Ring ID | Risk Level | Score | Customers | Accounts | Shared Assets | Recommended Action |
| --- | --- | --- | --- | --- | --- | --- |
| **RING-001** | `CRITICAL` | `1.0000` | 4 | 4 | Devs: 1, IPs: 1, Phones: 1 | FREEZE_LINKED_ACCOUNTS_AND_REFER_TO_FIU |

## 2. Circular Fund Transfer Loops

- **CYCLE-001** (3 hops, INR 194,300.00): `ACC-703 -> ACC-701 -> ACC-702 -> ACC-703`

## 3. Account Risk Evaluations

| Account | Risk Score | Risk Level | Ring Membership | Loops | Risk Summary |
| --- | --- | --- | --- | --- | --- |
| `ACC-801` | `1.0000` | `RingRiskLevel.CRITICAL` | `RING-001` | None | Member of fraud ring RING-001 (Syndicate Cluster #1 (SYNTHETIC_IDENTITY_DEVICE_SHARING)) |
| `ACC-701` | `0.7625` | `RingRiskLevel.CRITICAL` | `None` | CYCLE-001 | Participant in circular wash-trading loop CYCLE-001 ($194,300.00) |
| `ACC-600` | `0.7375` | `RingRiskLevel.HIGH` | `None` | None | High fan-in ratio (5 deposits vs 1 payouts) indicating money mule consolidation |
| `ACC-100045` | `0.0500` | `RingRiskLevel.LOW` | `None` | None | Standard isolated entity network pattern with no syndication indicators. |
