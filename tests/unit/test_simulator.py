"""
Comprehensive Unit Tests for Banking Transaction Simulator.
"""
from datetime import datetime, timezone
import pytest
from transaction_simulator.customer_generator import CustomerGenerator
from transaction_simulator.account_generator import AccountGenerator
from transaction_simulator.merchant_generator import MerchantGenerator
from transaction_simulator.device_generator import DeviceGenerator
from transaction_simulator.normal_generator import NormalTransactionGenerator
from transaction_simulator.fraud_scenarios import FraudScenarioEngine
from transaction_simulator.feature_engineer import FeatureEngineer


def test_customer_generator():
    gen = CustomerGenerator(seed=101)
    customers = gen.generate(count=50)
    assert len(customers) == 50
    assert customers[0]["customer_id"] == "CUS-200001"
    assert "email" in customers[0]
    assert "risk_segment" in customers[0]
    assert customers[0]["risk_segment"] in ["LOW", "STANDARD", "HIGH_NET_WORTH"]


def test_account_generator():
    cust_gen = CustomerGenerator(seed=102)
    customers = cust_gen.generate(count=20)

    acc_gen = AccountGenerator(seed=103)
    accounts = acc_gen.generate(customers)

    assert len(accounts) >= 20
    assert accounts[0]["account_id"].startswith("ACC-")
    assert accounts[0]["account_type"] in ["SAVINGS", "CURRENT", "CREDIT_CARD"]
    assert float(accounts[0]["balance"]) > 0


def test_merchant_generator():
    merch_gen = MerchantGenerator(seed=104)
    merchants = merch_gen.generate(count=30)
    assert len(merchants) == 30
    assert merchants[0]["merchant_id"].startswith("MER-")
    assert 0.0 <= merchants[0]["merchant_risk"] <= 1.0


def test_device_generator():
    cust_gen = CustomerGenerator(seed=105)
    customers = cust_gen.generate(count=15)

    dev_gen = DeviceGenerator(seed=106)
    devices = dev_gen.generate(customers)
    assert len(devices) >= 15
    assert devices[0]["device_id"].startswith("DEV-")
    assert devices[0]["primary_ip"].startswith("192.0.2.") or devices[0]["primary_ip"].startswith("198.51.100.") or devices[0]["primary_ip"].startswith("203.0.113.")


def test_all_eight_fraud_scenarios():
    engine = FraudScenarioEngine(seed=42)
    account = {"account_id": "ACC-100001", "balance": 150000.0}
    customer = {"customer_id": "CUS-200001", "city": "Mumbai", "country": "IN"}
    devices = [{"device_id": "DEV-40001", "primary_ip": "192.0.2.10"}]
    merchants = [
        {"merchant_id": "MER-90001", "merchant_category": "ELECTRONICS", "merchant_risk": 0.42},
        {"merchant_id": "MER-90002", "merchant_category": "JEWELRY", "merchant_risk": 0.55},
        {"merchant_id": "MER-90003", "merchant_category": "TRANSFER", "merchant_risk": 0.25},
        {"merchant_id": "MER-90004", "merchant_category": "GROCERY", "merchant_risk": 0.05},
        {"merchant_id": "MER-90005", "merchant_category": "TRAVEL", "merchant_risk": 0.38},
    ]
    curr_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)

    for scenario_name in FraudScenarioEngine.SCENARIO_NAMES:
        results = engine.inject_scenario(
            scenario_type=scenario_name,
            base_txn_id=f"TXN-TEST-{scenario_name}",
            account=account,
            customer=customer,
            customer_devices=devices,
            merchants=merchants,
            current_time=curr_time,
        )
        assert len(results) >= 1, f"Scenario {scenario_name} returned empty results"
        for txn, meta in results:
            assert "transaction_id" in txn
            assert "amount" in txn
            assert txn["amount"] > 0
            assert meta["scenario"] == scenario_name
            assert meta["severity"] in ["MEDIUM", "HIGH", "CRITICAL"]


def test_feature_engineering_no_target_leakage():
    devices = [{"device_id": "DEV-40001", "customer_id": "CUS-200001", "primary_ip": "192.0.2.10"}]
    accounts = [{"account_id": "ACC-100001", "account_age_days": 450}]
    merchants = [{"merchant_id": "MER-90001", "merchant_risk": 0.42}]

    txns = [
        {
            "transaction_id": "TXN-20261112-000001",
            "account_id": "ACC-100001",
            "customer_id": "CUS-200001",
            "amount": 5000.0,
            "merchant_id": "MER-90001",
            "device_id": "DEV-40001",
            "transaction_timestamp": "2026-11-12T10:00:00+00:00",
            "location": {"city": "Mumbai", "country": "IN"},
            "is_international": False
        },
        {
            "transaction_id": "TXN-20261112-000002",
            "account_id": "ACC-100001",
            "customer_id": "CUS-200001",
            "amount": 45000.0,
            "merchant_id": "MER-90001",
            "device_id": "DEV-ROGUE-99",
            "transaction_timestamp": "2026-11-12T10:03:00+00:00",
            "location": {"city": "Dubai", "country": "AE"},
            "is_international": True
        }
    ]

    fe = FeatureEngineer(registered_devices=devices, customer_accounts=accounts, merchants=merchants)
    features = fe.extract_features(txns)

    assert len(features) == 2
    f1 = features[0]
    f2 = features[1]

    # Verify no labels exist in feature dictionaries (Prevent target leakage)
    forbidden_keys = {"is_fraud", "fraud_label", "scenario_type", "scenario"}
    assert not forbidden_keys.intersection(f1.keys())
    assert not forbidden_keys.intersection(f2.keys())

    # Verify feature computations
    assert f1["new_device"] == 0
    assert f2["new_device"] == 1  # DEV-ROGUE-99 is unseen
    assert f2["transaction_count_5m"] == 1  # 1 prior transaction in 5m
    assert f2["international_flag"] == 1
    assert f2["location_change"] == 1
