"""Automated Compliance Evidence Collector and Posture Evaluator."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from compliance.control_mappings import get_default_control_mappings
from compliance.models import (
    ComplianceFramework,
    CompliancePostureSummary,
    ComplianceReport,
    ControlMapping,
    ControlStatus,
    EvidenceArtifact,
    FindingSeverity,
    FindingStatus,
    SecurityFinding,
)


class EvidenceCollector:
    """Collects security configuration evidence, evaluates compliance, and generates audit reports."""

    def __init__(self, environment: str = "production"):
        self.environment = environment

    def load_snapshot(self, snapshot_path: str) -> Dict[str, Any]:
        """Loads a security snapshot JSON file from disk."""
        path = Path(snapshot_path)
        if not path.exists():
            raise FileNotFoundError(f"Security snapshot file not found: {snapshot_path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def collect_from_snapshot(self, snapshot: Dict[str, Any]) -> ComplianceReport:
        """Parses snapshot data, compiles evidence artifacts, and scores regulatory controls."""
        artifacts: List[EvidenceArtifact] = []
        findings: List[SecurityFinding] = []
        controls = get_default_control_mappings()

        # 1. Parse CloudTrail Evidence
        ct_data = snapshot.get("cloudtrail", {})
        ct_enabled = ct_data.get("multi_region_enabled", False)
        ct_validation = ct_data.get("log_file_validation_enabled", False)
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-CLOUDTRAIL-LOGS",
                name="Multi-Region CloudTrail Trail Status",
                source="AWS::CloudTrail",
                payload=ct_data,
            )
        )

        # 2. Parse KMS Evidence
        kms_data = snapshot.get("kms", {})
        kms_rotated = kms_data.get("key_rotation_enabled", False)
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-KMS-ROTATION",
                name="KMS Customer Managed Key Rotation Status",
                source="AWS::KMS",
                payload=kms_data,
            )
        )

        # 3. Parse S3 Security Evidence
        s3_data = snapshot.get("s3", {})
        s3_encrypted = s3_data.get("all_buckets_encrypted", True)
        s3_public_blocked = s3_data.get("block_public_access_enabled", True)
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-S3-ENCRYPTION",
                name="S3 Data Lake Encryption & Public Block",
                source="AWS::S3",
                payload=s3_data,
            )
        )

        # 4. Parse Cognito Identity Evidence
        cognito_data = snapshot.get("cognito", {})
        cognito_mfa = cognito_data.get("mfa_configured", True)
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-COGNITO-CONFIG",
                name="Cognito User Pool RBAC & MFA Configuration",
                source="AWS::Cognito",
                payload=cognito_data,
            )
        )

        # 5. Parse GuardDuty & Security Hub Evidence
        gd_data = snapshot.get("guardduty", {})
        sh_data = snapshot.get("security_hub", {})
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-GUARDDUTY-STATUS",
                name="Amazon GuardDuty Detector State",
                source="AWS::GuardDuty",
                payload=gd_data,
            )
        )
        artifacts.append(
            EvidenceArtifact(
                evidence_id="EVID-SECURITYHUB-BENCHMARK",
                name="AWS Security Hub Standards Assessment",
                source="AWS::SecurityHub",
                payload=sh_data,
            )
        )

        # 6. Parse Security Findings
        raw_findings = snapshot.get("findings", [])
        for rf in raw_findings:
            sev_str = rf.get("severity", "MEDIUM").upper()
            try:
                sev = FindingSeverity(sev_str)
            except ValueError:
                sev = FindingSeverity.MEDIUM

            st_str = rf.get("status", "OPEN").upper()
            try:
                st = FindingStatus(st_str)
            except ValueError:
                st = FindingStatus.OPEN

            finding = SecurityFinding(
                finding_id=rf.get("finding_id", f"FIND-{uuid.uuid4().hex[:8]}"),
                title=rf.get("title", "Unclassified Security Alert"),
                description=rf.get("description", ""),
                severity=sev,
                status=st,
                source=rf.get("source", "SecurityHub"),
                resource_id=rf.get("resource_id", "arn:aws:::unknown"),
                resource_type=rf.get("resource_type", "AWS::Resource"),
                remediation_steps=rf.get("remediation_steps", ["Review cloud configuration."]),
            )
            findings.append(finding)

        # 7. Evaluate Controls based on Evidence
        for ctrl in controls:
            if ctrl.control_id == "SOC2-CC7.2":
                ctrl.status = ControlStatus.COMPLIANT if (ct_enabled and ct_validation) else ControlStatus.NON_COMPLIANT
            elif ctrl.control_id == "ISO-A.8.24":
                ctrl.status = ControlStatus.COMPLIANT if kms_rotated else ControlStatus.NON_COMPLIANT
            elif ctrl.control_id == "ISO-A.8.12":
                ctrl.status = ControlStatus.COMPLIANT if (s3_encrypted and s3_public_blocked) else ControlStatus.NON_COMPLIANT
            elif ctrl.control_id == "SOC2-CC6.1":
                ctrl.status = ControlStatus.COMPLIANT if cognito_mfa else ControlStatus.NON_COMPLIANT
            elif ctrl.control_id == "SOC2-CC7.1":
                ctrl.status = ControlStatus.COMPLIANT if gd_data.get("detector_enabled", True) else ControlStatus.NON_COMPLIANT
            else:
                ctrl.status = ControlStatus.COMPLIANT

        # 8. Compute Compliance Posture Summary
        total_ctrls = len(controls)
        compliant_ctrls = sum(1 for c in controls if c.status == ControlStatus.COMPLIANT)
        non_compliant_ctrls = sum(1 for c in controls if c.status == ControlStatus.NON_COMPLIANT)
        compliance_pct = round((compliant_ctrls / total_ctrls * 100), 1) if total_ctrls > 0 else 100.0

        # Framework Breakdown
        framework_scores: Dict[str, float] = {}
        for fw in ComplianceFramework:
            fw_ctrls = [c for c in controls if c.framework == fw]
            if fw_ctrls:
                fw_comp = sum(1 for c in fw_ctrls if c.status == ControlStatus.COMPLIANT)
                framework_scores[fw.value] = round((fw_comp / len(fw_ctrls)) * 100, 1)

        crit_findings = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL and f.status != FindingStatus.REMEDIATED)
        high_findings = sum(1 for f in findings if f.severity == FindingSeverity.HIGH and f.status != FindingStatus.REMEDIATED)
        open_findings = sum(1 for f in findings if f.status == FindingStatus.OPEN)

        posture = CompliancePostureSummary(
            framework_scores=framework_scores,
            total_controls=total_ctrls,
            compliant_controls=compliant_ctrls,
            non_compliant_controls=non_compliant_ctrls,
            compliance_percentage=compliance_pct,
            critical_findings_count=crit_findings,
            high_findings_count=high_findings,
            open_findings_count=open_findings,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

        return ComplianceReport(
            report_id=f"COMP-REP-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            environment=self.environment,
            posture=posture,
            controls=controls,
            findings=findings,
            evidence_artifacts=artifacts,
        )

    def save_report(self, report: ComplianceReport, output_dir: str) -> str:
        """Serializes the report to JSON and generates a Markdown audit summary."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        json_file = out_path / "compliance_report.json"
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        # Markdown summary
        md_file = out_path / "compliance_summary.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# FinGuard AI Compliance & Security Posture Report\n\n")
            f.write(f"- **Report ID:** `{report.report_id}`\n")
            f.write(f"- **Generated At:** {report.generated_at}\n")
            f.write(f"- **Environment:** `{report.environment}`\n")
            f.write(f"- **Overall Compliance:** **{report.posture.compliance_percentage}%**\n\n")

            f.write(f"## Regulatory Framework Scores\n\n")
            for fw, score in report.posture.framework_scores.items():
                f.write(f"- **{fw}:** {score}%\n")

            f.write(f"\n## Security Findings Overview\n\n")
            f.write(f"- Critical Findings: `{report.posture.critical_findings_count}`\n")
            f.write(f"- High Findings: `{report.posture.high_findings_count}`\n")
            f.write(f"- Total Open Findings: `{report.posture.open_findings_count}`\n\n")

            f.write(f"## Evaluated Security Controls ({len(report.controls)})\n\n")
            f.write(f"| Control ID | Framework | Title | Status |\n")
            f.write(f"| :--- | :--- | :--- | :--- |\n")
            for c in report.controls:
                f.write(f"| `{c.control_id}` | {c.framework.value} | {c.title} | **{c.status.value}** |\n")

        return str(json_file)

