"""Reference Control Mappings for SOC 2 Type II and ISO/IEC 27001:2022.

Maps regulatory and standard security controls to FinGuard AI cloud architecture,
automated evidence artifacts, and verification criteria.
"""

from typing import Dict, List
from compliance.models import ComplianceFramework, ControlMapping, ControlStatus


def get_default_control_mappings() -> List[ControlMapping]:
    """Returns the baseline regulatory control inventory for FinGuard AI."""
    return [
        # ========================================================
        # SOC 2 Type II — Common Criteria (Trust Services Criteria)
        # ========================================================
        ControlMapping(
            control_id="SOC2-CC6.1",
            framework=ComplianceFramework.SOC2,
            title="Logical Access Controls and Authentication",
            description="The entity restricts logical access to registered users via strong authentication and RBAC.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Amazon Cognito", "FastAPI Security Layer", "DynamoDB Audit"],
            evidence_ids=["EVID-COGNITO-CONFIG", "EVID-RBAC-MATRIX"],
            remediation_guidance="Enforce Cognito TOTP MFA and verify all protected endpoints validate JWT signatures.",
        ),
        ControlMapping(
            control_id="SOC2-CC6.6",
            framework=ComplianceFramework.SOC2,
            title="Boundary Protection and Perimeter Defense",
            description="Logical boundaries prevent unauthorized network access and enforce TLS 1.3.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["AWS WAF", "VPC Security Groups", "API Gateway"],
            evidence_ids=["EVID-VPC-TOPOLOGY", "EVID-TLS-POLICY"],
            remediation_guidance="Ensure all public-facing services terminate TLS 1.3 with strict cipher suites.",
        ),
        ControlMapping(
            control_id="SOC2-CC6.8",
            framework=ComplianceFramework.SOC2,
            title="Unauthorized Software & Change Management",
            description="Infrastructure changes and deployments are managed via version-controlled IaC and automated testing.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Terraform", "GitHub Actions CI/CD", "AWS CloudFormation"],
            evidence_ids=["EVID-TERRAFORM-PLAN", "EVID-CI-PIPELINE"],
            remediation_guidance="Enforce branch protection rules and mandatory peer reviews on Terraform modules.",
        ),
        ControlMapping(
            control_id="SOC2-CC7.1",
            framework=ComplianceFramework.SOC2,
            title="Vulnerability Detection and Continuous Monitoring",
            description="Continuous automated vulnerability scanning and threat detection identify emerging attack vectors.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Amazon GuardDuty", "AWS Security Hub", "AWS Config"],
            evidence_ids=["EVID-GUARDDUTY-STATUS", "EVID-SECURITYHUB-BENCHMARK"],
            remediation_guidance="Enable GuardDuty Runtime and S3 Malware Protection across active AWS regions.",
        ),
        ControlMapping(
            control_id="SOC2-CC7.2",
            framework=ComplianceFramework.SOC2,
            title="Security Event Monitoring and Incident Alerting",
            description="System anomalies and unauthorized access attempts are logged and trigger automated alarms.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["AWS CloudTrail", "Amazon CloudWatch", "Amazon SNS"],
            evidence_ids=["EVID-CLOUDTRAIL-LOGS", "EVID-CLOUDWATCH-ALARMS"],
            remediation_guidance="Verify multi-region CloudTrail logging is enabled with log file validation.",
        ),

        # ========================================================
        # ISO/IEC 27001:2022 — Information Security Controls
        # ========================================================
        ControlMapping(
            control_id="ISO-A.5.15",
            framework=ComplianceFramework.ISO27001,
            title="Access Control & Least Privilege",
            description="Access rights to assets and information are provisioned according to least privilege and role requirements.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Amazon Cognito", "AWS IAM", "FastAPI RBAC"],
            evidence_ids=["EVID-IAM-POLICIES", "EVID-RBAC-MATRIX"],
            remediation_guidance="Audit IAM roles quarterly and delete unused credentials with 90+ days inactivity.",
        ),
        ControlMapping(
            control_id="ISO-A.8.7",
            framework=ComplianceFramework.ISO27001,
            title="Protection Against Malware & Malicious Ingestion",
            description="Measures are implemented to prevent and detect malware in incoming streaming transactions and objects.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Amazon GuardDuty", "Lambda Sanitizer", "S3 Antivirus"],
            evidence_ids=["EVID-GUARDDUTY-STATUS"],
            remediation_guidance="Ensure all uploaded file evidence in S3 undergoes GuardDuty automated malware scanning.",
        ),
        ControlMapping(
            control_id="ISO-A.8.12",
            framework=ComplianceFramework.ISO27001,
            title="Data Leakage Prevention & Data Lake Isolation",
            description="Sensitive banking transactions and PII are protected against unauthorized exfiltration.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["Amazon S3", "AWS KMS", "AWS Glue"],
            evidence_ids=["EVID-S3-ENCRYPTION", "EVID-KMS-ROTATION"],
            remediation_guidance="Block all S3 public access and enforce customer-managed KMS keys with annual rotation.",
        ),
        ControlMapping(
            control_id="ISO-A.8.16",
            framework=ComplianceFramework.ISO27001,
            title="Monitoring Activities & Tamper-Evident Logging",
            description="Networks, systems, and user applications are monitored for anomalous behavior and security events.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["AWS CloudTrail", "DynamoDB Audit Store", "CloudWatch Logs"],
            evidence_ids=["EVID-CLOUDTRAIL-LOGS", "EVID-AUDIT-TABLE"],
            remediation_guidance="Verify DynamoDB security audit table has point-in-time recovery and KMS encryption.",
        ),
        ControlMapping(
            control_id="ISO-A.8.24",
            framework=ComplianceFramework.ISO27001,
            title="Cryptographic Controls and Key Management",
            description="Rules for the effective use of cryptography, including key management and rotation, are implemented.",
            status=ControlStatus.COMPLIANT,
            mapped_services=["AWS KMS", "TLS 1.3", "Secrets Manager"],
            evidence_ids=["EVID-KMS-ROTATION", "EVID-TLS-POLICY"],
            remediation_guidance="Ensure KMS CMK automatic annual key rotation is enabled across all storage targets.",
        ),
    ]

