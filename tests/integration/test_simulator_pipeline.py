"""
Integration Test for End-to-End Simulation Pipeline.
"""
import json
import os
import shutil
import tempfile
import pytest
from transaction_simulator.generator import BankingTransactionSimulator


def test_end_to_end_simulation_pipeline():
    temp_dir = tempfile.mkdtemp()
    try:
        sim = BankingTransactionSimulator(
            num_customers=50,
            num_transactions=250,
            fraud_rate=0.04,
            seed=42
        )
        report = sim.run(output_dir=temp_dir, formats=["csv", "jsonl"])

        # Check report contents
        assert report["summary"]["total_transactions"] == 250
        assert report["summary"]["fraudulent_transactions"] > 0
        assert report["summary"]["normal_transactions"] > 0

        # Check all files are created
        expected_files = [
            "customers.csv",
            "accounts.csv",
            "merchants.csv",
            "devices.csv",
            "transactions.csv",
            "transactions.jsonl",
            "fraud_labels.csv",
            "transaction_features.csv",
            "fraud_scenarios.csv",
            "dataset_report.json"
        ]

        for fname in expected_files:
            fpath = os.path.join(temp_dir, fname)
            assert os.path.exists(fpath), f"Missing generated file: {fname}"
            assert os.path.getsize(fpath) > 0, f"File {fname} is empty"

        # Check JSON report is valid
        with open(os.path.join(temp_dir, "dataset_report.json"), "r") as f:
            data = json.load(f)
            assert data["summary"]["total_transactions"] == 250
    finally:
        shutil.rmtree(temp_dir)

