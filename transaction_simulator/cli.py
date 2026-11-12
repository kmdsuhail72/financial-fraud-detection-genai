"""
Command Line Interface (CLI) for FinGuard AI Banking Transaction Simulator.
Provides the 'finguard-sim' command for dataset generation and benchmarking.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from transaction_simulator.generator import BankingTransactionSimulator


def main():
    parser = argparse.ArgumentParser(
        prog="finguard-sim",
        description="FinGuard AI — Banking Transaction Simulator & Fraud Dataset Generator"
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic banking and fraud datasets")
    gen_parser.add_argument(
        "--customers",
        type=int,
        default=1000,
        help="Number of synthetic customers to create (default: 1000)"
    )
    gen_parser.add_argument(
        "--transactions",
        type=int,
        default=20000,
        help="Number of total transactions to simulate (default: 20000)"
    )
    gen_parser.add_argument(
        "--fraud-rate",
        type=float,
        default=0.02,
        help="Target fraud ratio between 0.0 and 1.0 (default: 0.02 = 2%%)"
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic pseudorandom seed for reproducibility (default: 42)"
    )
    gen_parser.add_argument(
        "--output",
        type=str,
        default="data/generated",
        help="Output directory path for generated files (default: data/generated)"
    )
    gen_parser.add_argument(
        "--formats",
        nargs="+",
        choices=["csv", "jsonl", "parquet"],
        default=["csv", "jsonl"],
        help="Target output serialization formats (default: csv jsonl)"
    )
    gen_parser.add_argument(
        "--start-date",
        type=str,
        default="2026-11-01T00:00:00Z",
        help="Simulation start timestamp in ISO 8601 (default: 2026-11-01T00:00:00Z)"
    )

    args = parser.parse_args()

    if not args.subcommand or args.subcommand == "generate":
        # Default to generate if run without subcommand
        customers = getattr(args, "customers", 1000)
        transactions = getattr(args, "transactions", 20000)
        fraud_rate = getattr(args, "fraud_rate", 0.02)
        seed = getattr(args, "seed", 42)
        output_dir = getattr(args, "output", "data/generated")
        formats = getattr(args, "formats", ["csv", "jsonl"])
        start_date_str = getattr(args, "start_date", "2026-11-01T00:00:00Z")

        try:
            start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)

        print("\n=======================================================")
        print("FinGuard AI — Banking Transaction Simulator")
        print("=======================================================")
        print(f"[*] Synthetic Customers:    {customers:,}")
        print(f"[*] Total Transactions:     {transactions:,}")
        print(f"[*] Target Fraud Ratio:     {fraud_rate * 100:.2f}%")
        print(f"[*] Random Seed:            {seed}")
        print(f"[*] Output Directory:       {output_dir}")
        print(f"[*] Export Formats:         {', '.join(formats)}")
        print("-------------------------------------------------------")
        print("[*] Generating entities and simulating transaction stream...")

        sim = BankingTransactionSimulator(
            num_customers=customers,
            num_transactions=transactions,
            fraud_rate=fraud_rate,
            seed=seed,
            start_date=start_dt,
        )

        report = sim.run(output_dir=output_dir, formats=formats)

        print("[+] Simulation and feature engineering completed successfully!")
        print("\nDataset Summary Report:")
        print(json.dumps(report["summary"], indent=2))
        print("\nFraud Scenario Distribution:")
        print(json.dumps(report["fraud_scenario_breakdown"], indent=2))
        print(f"\n[+] Artifacts generated in: {os.path.abspath(output_dir)}")
        print("=======================================================\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
