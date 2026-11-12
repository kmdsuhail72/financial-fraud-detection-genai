"""
Master Banking Transaction Simulator Orchestrator.
Coordinates customer, account, merchant, normal transaction, fraud injection, and feature extraction.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from transaction_simulator.customer_generator import CustomerGenerator
from transaction_simulator.account_generator import AccountGenerator
from transaction_simulator.merchant_generator import MerchantGenerator
from transaction_simulator.device_generator import DeviceGenerator
from transaction_simulator.normal_generator import NormalTransactionGenerator
from transaction_simulator.fraud_scenarios import FraudScenarioEngine
from transaction_simulator.feature_engineer import FeatureEngineer
from transaction_simulator.exporter import DatasetExporter
from transaction_simulator.config import DEFAULT_SIMULATION_START


class BankingTransactionSimulator:
    """Master simulator orchestrator for FinGuard AI."""

    def __init__(
        self,
        num_customers: int = 1000,
        num_transactions: int = 20000,
        fraud_rate: float = 0.02,
        seed: int = 42,
        start_date: Optional[datetime] = None,
    ):
        self.num_customers = num_customers
        self.num_transactions = num_transactions
        self.fraud_rate = fraud_rate
        self.seed = seed
        self.start_date = start_date or DEFAULT_SIMULATION_START
        self.rng = random.Random(seed)

    def run(self, output_dir: str, formats: List[str] = ["csv", "jsonl"]) -> Dict:
        """
        Executes end-to-end dataset generation and exports all artifacts to output_dir.
        """
        # 1. Generate Foundation Entities
        cust_gen = CustomerGenerator(seed=self.seed)
        customers = cust_gen.generate(self.num_customers)

        acc_gen = AccountGenerator(seed=self.seed + 1)
        accounts = acc_gen.generate(customers)

        merch_gen = MerchantGenerator(seed=self.seed + 2)
        merchants = merch_gen.generate(count=max(50, self.num_customers // 5))

        dev_gen = DeviceGenerator(seed=self.seed + 3)
        devices = dev_gen.generate(customers)

        # Build index maps for fast lookups
        cust_map = {c["customer_id"]: c for c in customers}
        dev_map: Dict[str, List[Dict]] = {}
        for d in devices:
            dev_map.setdefault(d["customer_id"], []).append(d)

        # 2. Prepare Transaction Generators
        normal_gen = NormalTransactionGenerator(seed=self.seed + 4)
        fraud_engine = FraudScenarioEngine(seed=self.seed + 5)

        raw_transactions: List[Dict] = []
        fraud_labels: List[Dict] = []
        fraud_scenarios: List[Dict] = []

        # Target fraud count
        target_fraud_txns = max(1, int(self.num_transactions * self.fraud_rate))
        generated_fraud_count = 0

        # Scenario rotation
        scenario_cycle = list(FraudScenarioEngine.SCENARIO_NAMES)
        scenario_idx = 0

        # Simulation timeline over 10 days
        sim_duration_seconds = 10 * 86400
        time_step = sim_duration_seconds / max(1, self.num_transactions)

        current_time = self.start_date
        global_seq = 100000

        # 3. Generate Transactions Loop
        while len(raw_transactions) < self.num_transactions:
            global_seq += 1
            account = self.rng.choice(accounts)
            customer = cust_map[account["customer_id"]]
            cust_devices = dev_map.get(customer["customer_id"], [])

            # Advance simulation clock with slight jitter
            jitter = self.rng.uniform(0.5, 1.5)
            current_time += timedelta(seconds=time_step * jitter)

            # Determine whether to trigger a fraud scenario
            remaining_needed = target_fraud_txns - generated_fraud_count
            slots_left = self.num_transactions - len(raw_transactions)
            prob_fraud = (remaining_needed / slots_left) if slots_left > 0 else 0.0

            should_inject_fraud = (
                generated_fraud_count < target_fraud_txns
                and self.rng.random() < prob_fraud
            )

            if should_inject_fraud:
                scenario_type = scenario_cycle[scenario_idx % len(scenario_cycle)]
                scenario_idx += 1
                base_txn_id = f"TXN-20261112-{global_seq:06d}"

                fraud_items = fraud_engine.inject_scenario(
                    scenario_type=scenario_type,
                    base_txn_id=base_txn_id,
                    account=account,
                    customer=customer,
                    customer_devices=cust_devices,
                    merchants=merchants,
                    current_time=current_time,
                )

                for f_txn, f_meta in fraud_items:
                    raw_transactions.append(f_txn)
                    fraud_labels.append({"transaction_id": f_txn["transaction_id"], "is_fraud": 1})
                    fraud_scenarios.append({
                        "transaction_id": f_txn["transaction_id"],
                        "scenario_type": f_meta["scenario"],
                        "severity": f_meta["severity"],
                        "reason": f_meta["reason"],
                    })
                    generated_fraud_count += 1
            else:
                txn_id = f"TXN-20261112-{global_seq:06d}"
                norm_txn = normal_gen.generate_single(
                    transaction_id=txn_id,
                    account=account,
                    customer=customer,
                    customer_devices=cust_devices,
                    merchants=merchants,
                    current_time=current_time,
                )
                raw_transactions.append(norm_txn)
                fraud_labels.append({"transaction_id": txn_id, "is_fraud": 0})

        # Trim exact requested transaction size if burst exceeded slightly
        raw_transactions = raw_transactions[:self.num_transactions]
        valid_ids = {t["transaction_id"] for t in raw_transactions}
        fraud_labels = [f for f in fraud_labels if f["transaction_id"] in valid_ids]
        fraud_scenarios = [s for s in fraud_scenarios if s["transaction_id"] in valid_ids]

        # 4. Feature Engineering (Strictly isolated from labels)
        fe = FeatureEngineer(
            registered_devices=devices,
            customer_accounts=accounts,
            merchants=merchants,
        )
        features = fe.extract_features(raw_transactions)

        # 5. Export Datasets & Generate Report
        exporter = DatasetExporter(output_dir=output_dir)
        report = exporter.export(
            customers=customers,
            accounts=accounts,
            merchants=merchants,
            devices=devices,
            transactions=raw_transactions,
            fraud_labels=fraud_labels,
            features=features,
            fraud_scenarios=fraud_scenarios,
            formats=formats,
        )

        return report

