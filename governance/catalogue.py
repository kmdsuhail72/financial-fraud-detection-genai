"""
FinGuard AI — Phase 23 Compliance Catalogue.
Defines the 10 baseline regulatory controls mapped to SOC 2, ISO 27001, and PCI DSS.
"""
from __future__ import annotations

from typing import List
from governance.models import (
    ControlEffectiveness,
    FrameworkMapping,
    FrameworkType,
    GovernanceControl,
)


def get_starter_controls() -> List[GovernanceControl]:
    """Returns the 10 starter regulatory governance controls for FinGuard AI."""
    return [
        GovernanceControl(
            control_id="CTRL-IAM-01",
            name="Multi-Factor Authentication & Identity Lifecycle",
            domain="Identity and Access Management",
            description="Enforces phishing-resistant MFA, least-privilege role-based access control (RBAC), and automated credential revocation upon termination.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC6.1", description="Logical access restrictions via strong identity authentication."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.9.4.2", description="Secure log-on procedures and password systems."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 8.3", description="Multi-factor authentication for non-console administrative access."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-COGNITO-MFA-CONFIG", "EVD-RBAC-POLICY-DOC"],
            assessor_rationale="Cognito User Pool enforces TOTP MFA; FastAPI dependencies require valid verified JWT tokens with RBAC roles.",
        ),
        GovernanceControl(
            control_id="CTRL-CRYPTO-02",
            name="Cryptographic Key Management & Data Encryption",
            domain="Data Protection & Cryptography",
            description="Protects cardholder and customer PII at rest using AWS KMS envelope encryption (AES-256) and in transit using TLS 1.3.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC6.6", description="Boundary protection and transmission encryption."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.10.1.1", description="Cryptographic controls policy."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 3.4", description="Render PAN unreadable anywhere it is stored."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-KMS-KEY-POLICY", "EVD-TLS-CONFIG-REPORT"],
            assessor_rationale="All DynamoDB tables and S3 buckets enforce KMS SSE; API Gateway restricts ciphers to TLS 1.3.",
        ),
        GovernanceControl(
            control_id="CTRL-LOG-03",
            name="Tamper-Evident Audit Logging & Retention",
            domain="Security Operations & Auditing",
            description="Maintains immutable, append-only security and operational audit logs with SHA-256 verification and 365-day retention.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC7.2", description="Security event logging and unauthorized attempt detection."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.12.4.1", description="Event logging and administrator activity recording."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 10.2", description="Implement automated audit trails for all system components."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-DYNAMODB-AUDIT-SAMPLE", "EVD-CLOUDTRAIL-S3-LOCK"],
            assessor_rationale="Audit entries are logged synchronously with caller sub, email, action, and IP in append-only storage.",
        ),
        GovernanceControl(
            control_id="CTRL-VULN-04",
            name="Continuous Vulnerability Assessment & Patching",
            domain="Threat & Vulnerability Management",
            description="Executes automated static application security testing (SAST), software composition analysis (SCA), and container scans in CI/CD pipelines.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC7.1", description="Vulnerability detection and continuous monitoring."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.12.6.1", description="Management of technical vulnerabilities."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 6.2", description="Protect systems and networks from known vulnerabilities with vendor patches."),
            ],
            effectiveness=ControlEffectiveness.PARTIALLY_EFFECTIVE,
            evidence_references=["EVD-CI-SECURITY-PIPELINE", "EVD-DEPENDABOT-ALERTS"],
            assessor_rationale="GitHub Actions scans Python dependencies; automated container image runtime vulnerability scanning in ECR remains to be expanded.",
        ),
        GovernanceControl(
            control_id="CTRL-NET-05",
            name="Network Segmentation & Perimeter Protection",
            domain="Network Security",
            description="Isolates production databases and model inference nodes in private subnets with strict security groups and AWS WAF rate limiting.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC6.6", description="Network boundaries and DMZ architectures."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.13.1.1", description="Network controls and isolation of sensitive data."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 1.3", description="Restrict inbound and outbound traffic to that which is necessary."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-TERRAFORM-VPC-NET", "EVD-WAF-RULESET"],
            assessor_rationale="VPC architecture maintains private isolated subnets for Neptune and DynamoDB endpoints with VPC endpoints enabled.",
        ),
        GovernanceControl(
            control_id="CTRL-FRAUD-06",
            name="Real-Time Transaction Risk Scoring & AML Monitoring",
            domain="Financial Crime Compliance",
            description="Evaluates all incoming financial transactions across tabular ML, UEBA, Graph neural networks, and temporal sequence models within <50ms.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC6.8", description="Integrity of financial data processing systems."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.12.1.2", description="Change management and system operational procedures."),
                FrameworkMapping(framework=FrameworkType.FINCEN_AML, clause_or_requirement="Rule 31 CFR 1020.210", description="Customer identification and suspicious transaction monitoring program."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-PHASE20-FUSION-LOGS", "EVD-LATENCY-BENCHMARK"],
            assessor_rationale="Multi-signal decision engine evaluates 5 distinct detection signals with dynamic weight renormalization and P0-P3 SLA queues.",
        ),
        GovernanceControl(
            control_id="CTRL-INCIDENT-07",
            name="Enterprise Incident Response & SOC Containment",
            domain="Security Incident Response",
            description="Maintains defined response playbooks for fraud rings, account takeovers, and compromised credentials with human approval gates.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC7.3", description="Incident triage, response, and post-mortem procedures."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.16.1.1", description="Responsibilities and procedures for management of information security incidents."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 12.10", description="Implement an incident response plan to be prepared to respond immediately."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-SOC-PLAYBOOKS-CONFIG", "EVD-P0-DISPATCH-SLA"],
            assessor_rationale="Phase 12 SOC playbooks and Phase 21 Operations Queue enforce P0 (30m) and P1 (2h) strict response SLAs.",
        ),
        GovernanceControl(
            control_id="CTRL-FORENSICS-08",
            name="Digital Evidence Chain-of-Custody & SHA-256 Hashing",
            domain="Digital Forensics & Legal Admissibility",
            description="Indexes all forensic case artifacts with canonical SHA-256 cryptographic digests, verifying non-tampering before report sign-off.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC7.4", description="Containment and remediation of security incidents using verified evidence."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.16.1.7", description="Collection and preservation of legal digital evidence."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 10.5", description="Secure audit trails so they cannot be altered."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-SHA256-DIGEST-REGISTRY", "EVD-S3-OBJECT-LOCK"],
            assessor_rationale="Phase 22 Evidence Store validates canonical payloads and detects bit-level tampering on demand with audit logging.",
        ),
        GovernanceControl(
            control_id="CTRL-BACKUP-09",
            name="Disaster Recovery, Point-in-Time Recovery & Data Replication",
            domain="Business Continuity & Resilience",
            description="Enables automated continuous backups, multi-AZ high availability, and DynamoDB Point-in-Time Recovery (PITR) for all databases.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="A1.2", description="Environmental protections and data backup mechanisms."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.12.3.1", description="Information backup and redundancy."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 9.5", description="Physically protect and back up sensitive data storage."),
            ],
            effectiveness=ControlEffectiveness.EFFECTIVE,
            evidence_references=["EVD-DYNAMODB-PITR-STATUS", "EVD-S3-CROSS-REGION-REP"],
            assessor_rationale="Terraform configurations enable point_in_time_recovery = true on all DynamoDB tables across Phases 7 through 22.",
        ),
        GovernanceControl(
            control_id="CTRL-GOV-10",
            name="Risk Assessment, Third-Party Vendor & Policy Review",
            domain="Governance & Risk Management",
            description="Performs annual risk assessments, vendor security due diligence, and maintains formal financial crime governance policies.",
            framework_mappings=[
                FrameworkMapping(framework=FrameworkType.SOC2, clause_or_requirement="CC3.1", description="Risk identification, assessment, and vendor management."),
                FrameworkMapping(framework=FrameworkType.ISO27001, clause_or_requirement="A.6.1.2", description="Segregation of duties and external vendor review."),
                FrameworkMapping(framework=FrameworkType.PCI_DSS, clause_or_requirement="Requirement 12.1", description="Establish, publish, maintain, and disseminate a security policy."),
            ],
            effectiveness=ControlEffectiveness.PARTIALLY_EFFECTIVE,
            evidence_references=["EVD-ANNUAL-RISK-ASSESSMENT-2026", "EVD-VENDOR-REVIEWS"],
            assessor_rationale="Vendor risk review completed for primary cloud providers; quarterly third-party penetration testing is currently scheduled.",
        ),
    ]

