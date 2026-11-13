#!/usr/bin/env python3
"""
FinGuard AI — Threat Hunting CLI Tool (Phase 13).

Evaluates hypothesis-driven threat hunting rules across normalized security events,
correlating active threat intelligence indicators with MITRE ATT&CK technique mapping.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

from threat_intel.models import ThreatHuntingRule
from threat_intel.store import threat_intel_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hunt-events")


def run_hunting(events_file: str, rules_file: str, output_file: str):
    evt_path = Path(events_file)
    rul_path = Path(rules_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not evt_path.exists():
        logger.error("Events file not found: %s", evt_path)
        sys.exit(1)
    if not rul_path.exists():
        logger.error("Rules file not found: %s", rul_path)
        sys.exit(1)

    # Load events (JSON Lines or JSON array)
    events = []
    with open(evt_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                try:
                    events.append(json.loads(line_str))
                except json.JSONDecodeError:
                    continue

    # Load rules
    with open(rul_path, "r", encoding="utf-8") as f:
        raw_rules = json.load(f)

    rules = [ThreatHuntingRule.model_validate(r) for r in raw_rules]

    print("================================================================================")
    print("      FinGuard AI — Enterprise Threat Hunting & IOC Correlation                 ")
    print("================================================================================")
    print(f"[*] Security Events Input : {evt_path} ({len(events)} events)")
    print(f"[*] Threat Hunting Rules  : {rul_path} ({len(rules)} rules)")
    print(f"[*] Results Output Path   : {out_path}\n")

    results = threat_intel_store.hunter.hunt(rules=rules, events=events)

    print("-" * 80)
    print(f"HUNT FINDINGS: {len(results)} rule match(es) detected")
    print("-" * 80)

    for res in results:
        print(f"\n[!] MATCH: {res.rule_name} (Rule ID: {res.rule_id})")
        print(f"    MITRE Technique : {res.mitre_technique_id}")
        print(f"    Matched Events  : {len(res.matched_events)}")
        print(f"    Matched IOCs    : {', '.join(res.matched_iocs) if res.matched_iocs else 'None'}")
        print(f"    Finding Summary : {res.summary}")
        for evt in res.matched_events:
            print(f"      - Event ID: {evt.get('event_id')}, Source: {evt.get('source')}, Type: {evt.get('event_type')}")

    payload = {
        "summary": {
            "total_events_scanned": len(events),
            "total_rules_evaluated": len(rules),
            "total_hunt_findings": len(results),
        },
        "findings": [r.model_dump(mode="json") for r in results],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "-" * 80)
    print(f"[+] Saved threat hunting findings to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run threat hunting on security events")
    parser.add_argument("--events", default="examples/security_events.jsonl", help="Path to events JSONL")
    parser.add_argument("--rules", default="examples/hunt_rules.json", help="Path to hunting rules JSON")
    parser.add_argument("--output", default="artifacts/phase13/hunt-results.json", help="Output path")
    args = parser.parse_args()
    run_hunting(args.events, args.rules, args.output)

