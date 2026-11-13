#!/usr/bin/env python3
"""
FinGuard AI — IOC Enrichment CLI Tool (Phase 13).

Enriches raw indicators (IPv4, domains, URLs, hashes) using multi-provider threat intelligence
and local SQLite reputation cache, mapping findings to MITRE ATT&CK techniques.
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

# Disable AWS IMDS check for offline operations
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

from threat_intel.store import threat_intel_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrich-iocs")


def run_enrichment(input_file: str, output_file: str):
    in_path = Path(input_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        logger.error("Input file not found: %s", in_path)
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        indicators = json.load(f)

    if not isinstance(indicators, list):
        logger.error("Input JSON must be an array of indicator strings.")
        sys.exit(1)

    print("================================================================================")
    print("      FinGuard AI — Enterprise Threat Intelligence & IOC Enrichment            ")
    print("================================================================================")
    print(f"[*] Input Indicators File : {in_path} ({len(indicators)} indicators)")
    print(f"[*] Output Enriched File  : {out_path}\n")

    response = threat_intel_store.enrich_indicators(indicators=indicators)

    print("-" * 80)
    print(f"{'TYPE':<8} | {'INDICATOR':<38} | {'SCORE':<5} | {'SEVERITY':<8} | {'MITRE'}")
    print("-" * 80)

    for item in response.enriched:
        mitre_ids = [m.technique_id for m in item.mitre_attack]
        mitre_str = ", ".join(mitre_ids) if mitre_ids else "None"
        val_disp = item.value if len(item.value) <= 38 else item.value[:35] + "..."
        print(f"{item.type.value:<8} | {val_disp:<38} | {item.reputation_score:<5.1f} | {item.severity.value:<8} | {mitre_str}")

    if response.unrecognized:
        print("\n[!] Unrecognized / Invalid Syntax Indicators:")
        for u in response.unrecognized:
            print(f"  - {u}")

    # Save to output
    payload = {
        "summary": {
            "total_processed": response.total_processed,
            "total_enriched": len(response.enriched),
            "cache_hits": response.cache_hits,
            "unrecognized_count": len(response.unrecognized),
        },
        "enriched_iocs": [i.model_dump(mode="json") for i in response.enriched],
        "unrecognized": response.unrecognized,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("-" * 80)
    print(f"[+] Successfully saved {len(response.enriched)} enriched IOC(s) to: {out_path}")
    print(f"[+] Cache Hits: {response.cache_hits} | Newly Enriched: {len(response.enriched) - response.cache_hits}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich indicators of compromise")
    parser.add_argument("--input", default="examples/iocs.json", help="Path to input JSON file")
    parser.add_argument("--output", default="artifacts/phase13/enriched-iocs.json", help="Output path")
    args = parser.parse_args()
    run_enrichment(args.input, args.output)
