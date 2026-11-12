#!/usr/bin/env python3
"""
FinGuard AI — Automated Security Evidence Collector CLI.

Usage:
    python scripts/collect_evidence.py \
        --input examples/sample_security_snapshot.json \
        --output artifacts/phase11
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compliance.evidence_collector import EvidenceCollector


def main():
    parser = argparse.ArgumentParser(description="Collect and score security compliance evidence.")
    parser.add_argument(
        "--input",
        type=str,
        default="examples/sample_security_snapshot.json",
        help="Path to the security snapshot JSON file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/phase11",
        help="Output directory to store compliance reports and evidence manifests.",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="production",
        help="Target environment tag.",
    )

    args = parser.parse_args()

    collector = EvidenceCollector(environment=args.environment)
    print(f"[*] Ingesting security snapshot from: {args.input}")
    snapshot = collector.load_snapshot(args.input)

    print("[*] Evaluating regulatory controls against evidence...")
    report = collector.collect_from_snapshot(snapshot)

    print(f"[*] Writing compliance artifacts to: {args.output}")
    report_file = collector.save_report(report, args.output)

    print("\n=======================================================")
    print("  FinGuard AI — Compliance Evaluation Complete")
    print("=======================================================")
    print(f"  Report ID:               {report.report_id}")
    print(f"  Overall Compliance:      {report.posture.compliance_percentage}%")
    print(f"  Total Controls Scored:   {report.posture.total_controls}")
    print(f"  Compliant Controls:      {report.posture.compliant_controls}")
    print(f"  Non-Compliant Controls:  {report.posture.non_compliant_controls}")
    print(f"  Open Findings:           {report.posture.open_findings_count}")
    print(f"  Critical Findings:       {report.posture.critical_findings_count}")
    print(f"  High Findings:           {report.posture.high_findings_count}")
    print("-------------------------------------------------------")
    for fw, score in report.posture.framework_scores.items():
        print(f"  Framework [{fw}]: {score}%")
    print("=======================================================")
    print(f"[+] Output JSON: {report_file}")
    print(f"[+] Summary Doc: {Path(args.output) / 'compliance_summary.md'}\n")


if __name__ == "__main__":
    main()

