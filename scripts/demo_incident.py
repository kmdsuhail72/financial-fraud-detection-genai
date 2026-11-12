#!/usr/bin/env python3
"""
FinGuard AI — End-to-End SOC Incident Response Lifecycle Demonstration.

Usage:
    python scripts/demo_incident.py --output artifacts/phase12
"""

import argparse
import json
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from soc.event_normalizer import EventNormalizer
from soc.incident_store import SOCIncidentStore
from soc.models import ApprovalStatus


def main():
    parser = argparse.ArgumentParser(description="Demonstrate full SOC incident response lifecycle.")
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/phase12",
        help="Directory to save incident lifecycle report and execution receipt.",
    )
    args = parser.parse_args()

    print("\n=======================================================")
    print("  FinGuard AI — SOC Incident Response Lifecycle Demo")
    print("=======================================================\n")

    store = SOCIncidentStore()

    # Step 1: Ingest GuardDuty Security Finding Event
    print("[1] INGESTION: Receiving raw Amazon GuardDuty finding event...")
    raw_gd_event = {
        "id": "gd-alert-9901",
        "detail": {
            "type": "UnauthorizedAccess:IAMUser/AnomalousBehavior",
            "title": "Anomalous API Invocation via Compromised Role",
            "severity": 8.5,
            "resource": {
                "resourceType": "AWS::IAM::Role",
                "resourceId": "arn:aws:iam::123456789012:role/FinGuardPaymentProcessorRole",
            },
            "service": {
                "action": {
                    "awsApiCallAction": {
                        "remoteIpDetails": {"ipAddressV4": "198.51.100.42"}
                    }
                }
            },
        },
    }

    normalized_event = EventNormalizer.normalize(raw_gd_event)
    print(f"    Normalized: Event ID={normalized_event.event_id}, Severity={normalized_event.severity.value}, Fingerprint={normalized_event.fingerprint}")

    # Step 2: Incident Created & Correlated
    print("\n[2] INCIDENT CREATION: Provisioning SOC Incident Case with SLA tracking...")
    incident = store.ingest_event(normalized_event)
    print(f"    Incident ID:        {incident.incident_id}")
    print(f"    Title:              {incident.title}")
    print(f"    Initial Status:     {incident.status.value}")
    print(f"    SLA Target:         {incident.sla_target_minutes} minutes")

    # Step 3: AI Investigation Synthesis
    print("\n[3] AI INVESTIGATION: Synthesizing evidence-grounded threat brief...")
    if incident.ai_brief:
        print(f"    Synthesis Summary:  {incident.ai_brief.executive_summary}")
        print(f"    Tactical Hypotheses: {len(incident.ai_brief.hypotheses)} formulated")
        print(f"    Confidence:         {int(incident.ai_brief.confidence_score * 100)}%")

    # Step 4: Playbook Proposal
    print("\n[4] PLAYBOOK PROPOSED: Selecting containment actions...")
    playbook = incident.playbooks[0]
    action = playbook.actions[0]
    print(f"    Playbook:           {playbook.title}")
    print(f"    Action ID:          {action.action_id} ({action.name})")
    print(f"    Dry-Run Plan:       {action.dry_run_plan}")
    print(f"    Rollback Guidance:  {action.rollback_guidance}")
    print(f"    Requires Approval:  {action.requires_approval}")

    # Step 5: Separation of Duties & Human Approval Workflow
    print("\n[5] APPROVAL WORKFLOW: Enforcing human-in-the-loop governance...")
    requester = "analyst@finguard.internal"
    approver = "soc-lead@finguard.internal"
    approval_req = store.request_approval(incident.incident_id, action.action_id, requested_by=requester)
    print(f"    Approval Request:   {approval_req.approval_id} requested by {requester}")

    approval_done = store.approve_action(
        incident.incident_id,
        approval_req.approval_id,
        approver=approver,
        decision=ApprovalStatus.APPROVED,
        notes="Containment authorized following correlation verification.",
    )
    print(f"    Approval Decision:  {approval_done.status.value} by {approver}")

    # Step 6: Controlled Execution & Verification Receipt
    print("\n[6] EXECUTION & VERIFICATION: Running allowlisted simulation executor...")
    receipt = store.execute_remediation(incident.incident_id, action.action_id, executed_by=approver)
    print(f"    Receipt ID:         {receipt.receipt_id}")
    print(f"    Execution Status:   {receipt.execution_status}")
    print(f"    Verification:       {receipt.verification_results['execution_mode']}")
    print(f"    Updated State:      Incident status transitioned to {incident.status.value}")

    # Output artifact generation
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "incident_lifecycle_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(incident.model_dump_json(indent=2))

    md_path = out_dir / "incident_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# SOC Incident Investigation & Containment Report\n\n")
        f.write(f"- **Incident ID:** `{incident.incident_id}`\n")
        f.write(f"- **Severity:** **{incident.severity.value}**\n")
        f.write(f"- **Status:** `{incident.status.value}`\n")
        f.write(f"- **Primary Resource:** `{incident.primary_resource_id}`\n")
        f.write(f"- **SLA Target:** {incident.sla_target_minutes} mins (Compliant)\n\n")

        f.write(f"## AI Investigation Brief\n\n")
        if incident.ai_brief:
            f.write(f"{incident.ai_brief.executive_summary}\n\n")
            f.write(f"### Recommended Checks\n")
            for chk in incident.ai_brief.recommended_checks:
                f.write(f"- {chk}\n")

        f.write(f"\n## Containment Actions Executed\n\n")
        f.write(f"- Action: `{action.name}`\n")
        f.write(f"- Approved By: `{approver}`\n")
        f.write(f"- Receipt: `{receipt.receipt_id}` ({receipt.execution_status})\n\n")

        f.write(f"## Audit Timeline ({len(incident.timeline)} entries)\n\n")
        f.write(f"| Timestamp | Author | Action | Description |\n")
        f.write(f"| :--- | :--- | :--- | :--- |\n")
        for t in incident.timeline:
            f.write(f"| {t.timestamp} | `{t.author}` | {t.entry_type} | {t.description} |\n")

    print("\n=======================================================")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Summary Doc: {md_path}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()

