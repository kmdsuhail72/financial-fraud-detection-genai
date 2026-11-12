# Phase 10: Enterprise Authentication, Authorization, RBAC and Security Governance

## 1. Security Architecture Overview

Phase 10 implements an enterprise-grade defense-in-depth security model for **FinGuard AI**, combining Amazon Cognito identity management, OIDC JWT authorization code grant with PKCE, server-side RBAC dependencies in FastAPI, and tamper-evident DynamoDB security audit logging.

```
+-----------------------------------------------------------------------------------+
|                            React Analyst Portal (SPA)                             |
|  - OIDC PKCE Authorization Code Grant (No Client Secret)                          |
|  - Dynamic UI Permission Guards (Active Role Switching in Sandbox)                |
+-----------------------------------------+-----------------------------------------+
                                          |
                        Bearer JWT Token (RS256 / JWKS)
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        FastAPI Security Middleware Layer                          |
|  - JWKS Signature & Issuer Verification (Cognito User Pool)                       |
|  - Expiration & Token Use ('access'/'id') Validation                              |
|  - Server-Side RBAC Enforcement: require_permission(...) & require_roles(...)     |
+-----------------------------------------+-----------------------------------------+
                                          |
         +--------------------------------+--------------------------------+
         |                                                                 |
         v                                                                 v
+----------------------------------+             +----------------------------------+
|    Protected API Operations      |             |    DynamoDB Security Audit Table |
|  - GET  /cases                   |             |    (finguard-dev-security-audit) |
|  - POST /cases/{id}/assign       |             |  - Actor, Action, Resource       |
|  - POST /cases/{id}/notes        |             |  - Timestamp, Status, Client IP  |
|  - POST /cases/{id}/escalate     |             |  - Immutable Point-in-Time Log   |
|  - POST /cases/{id}/resolve      |             +----------------------------------+
|  - GET  /audit/logs              |
|  - POST /users/roles             |
+----------------------------------+
```

---

## 2. Roles & Permissions Matrix

All capabilities are strictly enforced at the API layer. The UI reflects these rules, but hiding controls in React is never treated as a security boundary.

| Capability | Admin | Investigator | Analyst | Auditor | Granular Permission Code |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **View Cases** | YES | YES | YES | YES | `cases:view` |
| **Assign Cases** | YES | YES | — | — | `cases:assign` |
| **Add Investigation Notes** | YES | YES | YES | — | `cases:notes:add` |
| **Escalate Cases** | YES | YES | YES | — | `cases:escalate` |
| **Resolve Cases (Verdict)** | YES | YES | — | — | `cases:resolve` |
| **View Audit History** | YES | — | — | YES | `audit:view` |
| **Manage Users & Roles** | YES | — | — | — | `users:manage` |

---

## 3. Terraform Cloud Security Foundation

The infrastructure is defined in `infrastructure/terraform/phase10/`:
- **Cognito User Pool**: MFA (TOTP), 12+ character complex password policy, encrypted attributes.
- **Cognito App Client**: Public client with `generate_secret = false` for SPA security with PKCE.
- **User Groups**: `Admin` (precedence 1), `Investigator` (precedence 10), `Analyst` (precedence 20), `Auditor` (precedence 30).
- **DynamoDB Security Audit Table**: Server-side KMS encryption, GSI on `actor_email` and `timestamp`, Point-In-Time-Recovery (PITR).

