#!/usr/bin/env python3
"""
FinGuard AI — Enterprise Disaster Recovery Assessment & Failover Planning CLI.
Usage:
    python scripts/assess_dr.py targets [--json]
    python scripts/assess_dr.py assess <service_id> --rto <rto_min> --rpo <rpo_min> [--json]
    python scripts/assess_dr.py failover-plan [--primary-healthy] [--secondary-ready] --lag <lag_min> [--json]
"""
import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path so disaster_recovery can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from disaster_recovery.service import dr_service


def cmd_targets(args: argparse.Namespace) -> None:
    targets = dr_service.list_targets()
    if args.json:
        print(json.dumps([t.model_dump() for t in targets], indent=2))
        return

    print("=" * 80)
    print(" FinGuard AI — Disaster Recovery Targets (RTO / RPO Objectives)")
    print("=" * 80)
    print(f"{'Service ID':<25} {'Priority':<10} {'Target RTO':<12} {'Target RPO':<12} {'Tier'}")
    print("-" * 80)
    for t in targets:
        print(f"{t.service_id:<25} {t.priority.value:<10} {t.target_rto_min} min{'':<6} {t.target_rpo_min} min{'':<6} {t.tier}")
    print("-" * 80)


def cmd_assess(args: argparse.Namespace) -> None:
    assessment = dr_service.assess_recovery(
        service_id=args.service,
        measured_rto_min=args.rto,
        measured_rpo_min=args.rpo,
    )
    if not assessment:
        print(f"Error: Service '{args.service}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(assessment.model_dump(), indent=2))
        return

    print("=" * 70)
    print(f" Recovery Assessment: {assessment.name} ({assessment.service_id})")
    print("=" * 70)
    print(f" Status:              {assessment.status.value}")
    print(f" Overall Compliant:   {'YES' if assessment.overall_compliant else 'NO'}")
    print(f" Measured RTO:        {assessment.measured_rto_min} min (Target: <= {assessment.target_rto_min} min) -> {'PASS' if assessment.rto_compliant else 'FAIL'}")
    print(f" Measured RPO:        {assessment.measured_rpo_min} min (Target: <= {assessment.target_rpo_min} min) -> {'PASS' if assessment.rpo_compliant else 'FAIL'}")
    if not assessment.overall_compliant:
        print(f" RTO Gap:             +{assessment.gap_rto_min} min")
        print(f" RPO Gap:             +{assessment.gap_rpo_min} min")
    print("=" * 70)


def cmd_failover_plan(args: argparse.Namespace) -> None:
    plan = dr_service.generate_failover_plan(
        primary_healthy=args.primary_healthy,
        secondary_ready=args.secondary_ready,
        replication_lag_min=args.lag,
        authorized_by=args.authorized_by,
    )

    if args.json:
        print(json.dumps(plan.model_dump(), indent=2))
        return

    print("=" * 80)
    print(f" FinGuard Multi-Region Failover Proposal ({plan.proposal_id})")
    print("=" * 80)
    print(f" Primary Region:      {plan.primary_region} (Healthy: {plan.primary_healthy})")
    print(f" Secondary Region:    {plan.secondary_region} (Ready: {plan.secondary_ready})")
    print(f" Measured Rep Lag:    {plan.replication_lag_min} min (Max Allowed RPO: {plan.max_allowed_rpo_min} min)")
    print(f" Recommended Action:  {plan.recommended_action.value}")
    print(f" Approved by Engine:  {'YES' if plan.approved_for_failover else 'NO'}")
    print(f" Human Approval:      REQUIRED (Operator sign-off gate enforced)")
    print("-" * 80)
    print(f" Rationale: {plan.rationale}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="FinGuard AI Disaster Recovery Assessment CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # targets
    p_targets = subparsers.add_parser("targets", help="List recovery targets and RTO/RPO objectives")
    p_targets.add_argument("--json", action="store_true", help="Output results in JSON format")

    # assess
    p_assess = subparsers.add_parser("assess", help="Assess recovery measurements against target objectives")
    p_assess.add_argument("service", type=str, help="Service ID (e.g. transaction-ingestion)")
    p_assess.add_argument("--rto", type=float, required=True, help="Measured RTO in minutes")
    p_assess.add_argument("--rpo", type=float, required=True, help="Measured RPO in minutes")
    p_assess.add_argument("--json", action="store_true", help="Output results in JSON format")

    # failover-plan
    p_plan = subparsers.add_parser("failover-plan", help="Generate multi-region failover proposal")
    p_plan.add_argument("--primary-healthy", action="store_true", default=False, help="Set if primary region is healthy")
    p_plan.add_argument("--secondary-ready", action="store_true", default=False, help="Set if secondary region is ready")
    p_plan.add_argument("--lag", type=float, required=True, help="Replication lag in minutes")
    p_plan.add_argument("--authorized-by", type=str, default=None, help="Operator name authorizing review")
    p_plan.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    if args.command == "targets":
        cmd_targets(args)
    elif args.command == "assess":
        cmd_assess(args)
    elif args.command == "failover-plan":
        cmd_failover_plan(args)


if __name__ == "__main__":
    main()
