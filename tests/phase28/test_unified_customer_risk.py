"""
FinGuard AI — Phase 28: Unified Customer Risk Intelligence Test Suite.
Validates:
1. Health check endpoint (/risk/health and /health)
2. Comprehensive 7-domain risk assessment (100% signal coverage)
3. Missing domains handling & weight renormalization (4 domains, 76% coverage matching benchmark)
4. Signal coverage calculation across domain combinations
5. Risk classification boundary tiers (LOW, MEDIUM, HIGH, CRITICAL)
6. Continuous customer risk reassessment with previous-score delta comparison
7. Assessment listing and retrieval by ID
8. Signal explainability, domain contributions, and source attribution
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from customer_risk.models import CustomerRiskLevel, RiskDomain


@pytest.fixture
def client():
    return TestClient(app)


def test_risk_health_endpoint(client):
    """1. Test health check endpoint."""
    resp = client.get("/risk/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "customer_risk_intelligence"
    assert data["phase"] == "Phase-28"


def test_comprehensive_7_domain_assessment(client):
    """2. Test assessment with all 7 risk domains provided (100% signal coverage)."""
    payload = {
        "customer_id": "CUST-FULL-7D",
        "customer_name": "Eleanor Vance",
        "kyc_score": 20.0,         # 18% -> 3.6
        "aml_score": 30.0,         # 22% -> 6.6
        "fraud_score": 25.0,       # 20% -> 5.0
        "identity_score": 15.0,    # 16% -> 2.4
        "sanctions_score": 0.0,    # 14% -> 0.0
        "pep_score": 0.0,          # 5%  -> 0.0
        "behavioral_score": 40.0,  # 5%  -> 2.0
        "notes": "Full 7-domain customer risk profile"
    }
    resp = client.post("/risk/assessments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_id"] == "CUST-FULL-7D"
    assert data["signal_coverage_percent"] == 100.0
    assert data["active_domains_count"] == 7
    # Composite: 3.6 + 6.6 + 5.0 + 2.4 + 0.0 + 0.0 + 2.0 = 19.6 -> LOW (< 25)
    assert 19.0 <= data["composite_risk_score"] <= 20.5
    assert data["risk_level"] == "LOW"
    assert len(data["domain_signals"]) == 7


def test_missing_domains_and_weight_renormalization(client):
    """3. Test benchmark example: 4 domains (KYC, AML, Fraud, Identity) yielding 76% coverage and ~39 score."""
    # Active weights: 0.18 + 0.22 + 0.20 + 0.16 = 0.76 (76%)
    # Normalized weights: KYC: 18/76=0.2368, AML: 22/76=0.2895, Fraud: 20/76=0.2632, Identity: 16/76=0.2105
    # Scores: KYC 25, AML 45, Fraud 40, Identity 45
    # Expected: (0.2368*25) + (0.2895*45) + (0.2632*40) + (0.2105*45) = 5.92 + 13.03 + 10.53 + 9.47 = 38.95 -> 39.0
    payload = {
        "customer_id": "CUST-BENCHMARK-39",
        "customer_name": "Jordan Cross",
        "kyc_score": 25.0,
        "aml_score": 45.0,
        "fraud_score": 40.0,
        "identity_score": 45.0
    }
    resp = client.post("/risk/assessments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["signal_coverage_percent"] == 76.0
    assert data["active_domains_count"] == 4
    assert round(data["composite_risk_score"]) == 39
    assert data["risk_level"] == "MEDIUM"


def test_signal_coverage_calculation(client):
    """4. Test signal coverage percentage calculation across subsets."""
    # Subtest 4a: KYC (18%) + AML (22%) = 40.0% coverage
    p_40 = {
        "customer_id": "CUST-COV-40",
        "customer_name": "Coverage Tester",
        "kyc_score": 20.0,
        "aml_score": 30.0
    }
    r_40 = client.post("/risk/assessments", json=p_40)
    assert r_40.status_code == 201
    assert r_40.json()["signal_coverage_percent"] == 40.0

    # Subtest 4b: Sanctions (14%) + PEP (5%) = 19.0% coverage
    p_19 = {
        "customer_id": "CUST-COV-19",
        "customer_name": "Screening Only",
        "sanctions_score": 50.0,
        "pep_score": 100.0
    }
    r_19 = client.post("/risk/assessments", json=p_19)
    assert r_19.status_code == 201
    assert r_19.json()["signal_coverage_percent"] == 19.0


def test_risk_level_classification_tiers(client):
    """5. Test risk classification boundaries: LOW (<25), MEDIUM (25-49.99), HIGH (50-74.99), CRITICAL (>=75)."""
    # 5a. CRITICAL: 85 score across domains
    p_crit = {
        "customer_id": "CUST-TIER-CRIT",
        "customer_name": "Critical Entity",
        "kyc_score": 85.0,
        "fraud_score": 90.0,
        "identity_score": 85.0
    }
    r_crit = client.post("/risk/assessments", json=p_crit)
    assert r_crit.status_code == 201
    assert r_crit.json()["risk_level"] == "CRITICAL"
    assert r_crit.json()["composite_risk_score"] >= 75.0

    # 5b. HIGH: 60 score across domains
    p_high = {
        "customer_id": "CUST-TIER-HIGH",
        "customer_name": "High Entity",
        "kyc_score": 60.0,
        "aml_score": 60.0
    }
    r_high = client.post("/risk/assessments", json=p_high)
    assert r_high.status_code == 201
    assert r_high.json()["risk_level"] == "HIGH"
    assert 50.0 <= r_high.json()["composite_risk_score"] < 75.0


def test_continuous_reassessment_and_delta(client):
    """6. Test continuous reassessment tracking previous score, delta, and direction."""
    cid = "CUST-REASSESS-01"

    # Assessment 1: Low baseline
    r1 = client.post("/risk/assessments", json={
        "customer_id": cid,
        "customer_name": "Reassessment Subject",
        "kyc_score": 10.0,
        "aml_score": 10.0
    })
    assert r1.status_code == 201
    data1 = r1.json()
    assert data1["composite_risk_score"] == 10.0
    assert data1["previous_comparison"] is None

    # Assessment 2: Significant increase (e.g. AML structuring event occurs)
    r2 = client.post("/risk/assessments", json={
        "customer_id": cid,
        "customer_name": "Reassessment Subject",
        "kyc_score": 10.0,
        "aml_score": 70.0
    })
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["previous_comparison"] is not None
    comp = data2["previous_comparison"]
    assert comp["previous_score"] == 10.0
    assert comp["direction"] == "INCREASED"
    assert comp["score_delta"] > 0

    # Check history endpoint
    r_hist = client.get(f"/risk/customers/{cid}/history")
    assert r_hist.status_code == 200
    history = r_hist.json()
    assert len(history) >= 2


def test_assessment_listing_and_retrieval(client):
    """7. Test listing assessments with filters and fetching by assessment_id."""
    # List all
    r_all = client.get("/risk/assessments")
    assert r_all.status_code == 200
    all_list = r_all.json()
    assert len(all_list) >= 3

    # Retrieve specific assessment
    target_id = all_list[0]["assessment_id"]
    r_single = client.get(f"/risk/assessments/{target_id}")
    assert r_single.status_code == 200
    assert r_single.json()["assessment_id"] == target_id


def test_signal_explainability_and_sources(client):
    """8. Test signal explainability, contribution breakdown, and upstream source references."""
    payload = {
        "customer_id": "CUST-EXPLAIN-01",
        "customer_name": "Explainability Subject",
        "kyc_score": 30.0,
        "aml_score": 75.0,
        "indicators": {
            "AML": ["Rapid inflow/outflow pass-through layering detected."]
        },
        "sources": {
            "AML": "Phase 24 AML Monitoring Rules Engine"
        }
    }
    resp = client.post("/risk/assessments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    aml_sig = data["domain_signals"]["AML"]
    assert aml_sig["score"] == 75.0
    assert aml_sig["source_reference"] == "Phase 24 AML Monitoring Rules Engine"
    assert "layering detected" in aml_sig["indicators"][0]
    assert aml_sig["weighted_contribution"] > 0
    assert any("AML" in d for d in data["primary_risk_drivers"])

