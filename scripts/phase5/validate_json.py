"""
Bronze JSON Dataset Validator.
Recursively inspects JSON files for structural integrity and required banking fields.
"""
import argparse
import json
import os
import sys
from typing import Dict, List, Tuple

REQUIRED_FIELDS = [
    "transaction_id",
    "account_id",
    "customer_id",
    "amount",
    "currency",
    "channel",
    "transaction_timestamp",
    "features"
]


def validate_json_directory(input_dir: str) -> Tuple[int, int, List[str]]:
    """
    Validates all JSON files in the specified directory.
    Returns (total_files, valid_records, error_list).
    """
    if not os.path.exists(input_dir):
        return 0, 0, [f"Directory not found: {input_dir}"]

    total_files = 0
    valid_records = 0
    errors = []

    for root, _, files in os.walk(input_dir):
        for fname in files:
            if fname.endswith(".json") or fname.endswith(".jsonl"):
                total_files += 1
                fpath = os.path.join(root, fname)

                with open(fpath, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        clean_line = line.strip()
                        if not clean_line:
                            continue

                        try:
                            record = json.loads(clean_line)
                            missing = [rf for rf in REQUIRED_FIELDS if rf not in record]
                            if missing:
                                errors.append(f"{fpath}:{line_no} Missing required fields: {missing}")
                            elif float(record.get("amount", 0)) <= 0:
                                errors.append(f"{fpath}:{line_no} Invalid amount: {record.get('amount')}")
                            else:
                                valid_records += 1
                        except Exception as err:
                            errors.append(f"{fpath}:{line_no} Malformed JSON: {str(err)}")

    return total_files, valid_records, errors


def main():
    parser = argparse.ArgumentParser(description="Validate Bronze JSON Data Lake Files")
    parser.add_argument("--input", type=str, default="data/phase5-sample", help="Input directory")
    args = parser.parse_args()

    print(f"Scanning Bronze JSON files in: {args.input}")
    total_files, valid_records, errors = validate_json_directory(args.input)

    print(f"[*] Total partition files inspected: {total_files}")
    print(f"[*] Valid transaction records:       {valid_records}")
    print(f"[*] Errors detected:                 {len(errors)}")

    if errors:
        print("\nErrors encountered:")
        for e in errors[:10]:
            print(f"  - {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more.")
        sys.exit(1)
    else:
        print("[+] All Bronze JSON records are structurally valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()

