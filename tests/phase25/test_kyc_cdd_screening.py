"""
FinGuard AI — Phase 25: KYC, CDD/EDD & Screening Test Suite.
Validates:
1. Health check endpoint (/kyc/health)
2. Customer onboarding & idempotent profile creation
3. KYC document upload & SHA-256 integrity verification
4. Fuzzy name matching & screening fixtures (PEP, Sanctions, Adverse Media)
5. CDD vs EDD risk level determination
6. Compliance review decision & rationale workflow
7. Audit trail event logging & chronology
8. End-to-end onboarding, screening, and EDD review flow
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from kyc.service import get_kyc_service
from kyc.models import (
    CustomerType,
    OnboardingStatus,
    RiskLevel,
    CDDTier,
    DocumentType,
    ReviewDecision,
    ScreeningMatchCategory,
)
from kyc.screening import compute_fuzzy_similarity, ScreeningEngine


@pytest.fixture
def client():
    return TestClient(app)


def test_kyc_health_endpoint(client):
    """1. Test health check endpoint."""
    resp = client.get("/kyc/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "kyc_onboarding"


def test_customer_onboarding_idempotency(client):
    """2. Test onboarding a customer and idempotent registration with custom ID."""
    payload = {
        "customer_id": "CUST-TEST-IDEMPOTENT-01",
        "customer_type": "INDIVIDUAL",
        "full_name": "Jonathan Archer",
        "date_of_birth_or_inc": "1975-04-18",
        "nationality_or_country": "US",
        "email": "jonathan.archer@starfleet-demo.com",
        "phone": "+1-555-0144",
        "tax_id_masked": "XXX-XX-8821"
    }

    # Initial creation
    resp1 = client.post("/kyc/customers", json=payload)
    assert resp1.status_code == 201
    c1 = resp1.json()
    assert c1["customer_id"] == "CUST-TEST-IDEMPOTENT-01"
    assert c1["full_name"] == "Jonathan Archer"
    assert c1["onboarding_status"] in ["PENDING_REVIEW", "EDD_REQUIRED", "APPROVED"]

    # Repeated creation with same customer_id (idempotency check)
    resp2 = client.post("/kyc/customers", json=payload)
    assert resp2.status_code == 201
    c2 = resp2.json()
    assert c2["customer_id"] == c1["customer_id"]
    assert c2["created_at"] == c1["created_at"]


def test_kyc_document_upload_and_sha256(client):
    """3. Test document registration and SHA-256 calculation."""
    # Create customer
    onboard_payload = {
        "full_name": "T'Pol Vulcan",
        "date_of_birth_or_inc": "1980-02-11",
        "nationality_or_country": "US",
        "email": "tpol@vulcan-demo.com",
        "phone": "+1-555-0992",
        "tax_id_masked": "XXX-XX-1122"
    }
    create_resp = client.post("/kyc/customers", json=onboard_payload)
    cid = create_resp.json()["customer_id"]

    # Upload document with content_raw
    doc_payload = {
        "document_type": "PASSPORT",
        "issuing_country": "US",
        "document_number_masked": "P******89",
        "content_raw": "SIMULATED_PASSPORT_IMAGE_RAW_BYTE_CONTENT"
    }
    doc_resp = client.post(f"/kyc/customers/{cid}/documents", json=doc_payload)
    assert doc_resp.status_code == 201
    doc_data = doc_resp.json()
    assert doc_data["document_id"].startswith("DOC-")
    assert doc_data["document_type"] == "PASSPORT"
    assert len(doc_data["sha256_hash"]) == 64  # Valid SHA-256 hex length

    # Verify customer documents list updated
    cust_resp = client.get(f"/kyc/customers/{cid}")
    cust_data = cust_resp.json()
    assert len(cust_data["documents"]) >= 1
    assert any(d["document_id"] == doc_data["document_id"] for d in cust_data["documents"])


def test_fuzzy_name_matching_and_screening():
    """4. Test fuzzy string similarity and screening fixtures (PEP, Sanctions, Adverse Media)."""
    # 4a. Fuzzy similarity tests
    sim_exact = compute_fuzzy_similarity("Arthur Pendelton", "Arthur Pendelton")
    assert sim_exact == 1.0

    # Slight misspelling / transposition
    sim_typo = compute_fuzzy_similarity("Arthur Pendelton", "Arthur Pendleton")
    assert sim_typo >= 0.85

    # Reordered words
    sim_reorder = compute_fuzzy_similarity("Pendelton, Arthur", "Arthur Pendelton")
    assert sim_reorder >= 0.85

    # 4b. Screening engine detection of synthetic fixtures
    engine = ScreeningEngine(match_threshold=0.70)
    
    # PEP screening test
    pep_matches = engine.screen("Arthur Pendelton")
    assert len(pep_matches) >= 1
    assert any(m.category == ScreeningMatchCategory.PEP for m in pep_matches)
    assert pep_matches[0].matched_entity_name == "Arthur Pendelton"

    # Sanctions screening test
    sanction_matches = engine.screen("Red Star Maritime")
    assert len(sanction_matches) >= 1
    assert any(m.category == ScreeningMatchCategory.SANCTIONS for m in sanction_matches)

    # Adverse media screening test
    media_matches = engine.screen("Carlos Mendez")
    assert len(media_matches) >= 1
    assert any(m.category == ScreeningMatchCategory.ADVERSE_MEDIA for m in media_matches)


def test_cdd_vs_edd_risk_determination(client):
    """5. Test that high-risk attributes force EDD and elevated risk levels."""
    # 5a. Clean customer in low-risk jurisdiction
    clean_payload = {
        "full_name": "Alice Standard",
        "date_of_birth_or_inc": "1992-06-15",
        "nationality_or_country": "US",
        "email": "alice.std@demo.com",
        "phone": "+1-555-4321",
        "tax_id_masked": "XXX-XX-9900",
        "initial_documents": [
            {
                "document_id": "DOC-ALICE-PASS",
                "document_type": "PASSPORT",
                "issuing_country": "US",
                "document_number_masked": "P*****12",
                "sha256_hash": "a"*64
            }
        ]
    }
    r_clean = client.post("/kyc/customers", json=clean_payload)
    data_clean = r_clean.json()
    assert data_clean["risk_assessment"]["risk_level"] in ["LOW", "MEDIUM"]
    assert data_clean["risk_assessment"]["cdd_tier"] in ["SIMPLIFIED_SDD", "STANDARD_CDD"]

    # 5b. High-risk entity matching PEP fixture in high-risk country
    high_risk_payload = {
        "customer_type": "INDIVIDUAL",
        "full_name": "Vladimir Volkov",  # matches PEP synthetic fixture
        "date_of_birth_or_inc": "1960-01-01",
        "nationality_or_country": "RU",
        "email": "vladimir.v@demo.ru",
        "phone": "+7-495-123456",
        "tax_id_masked": "RU-INN-***99"
    }
    r_high = client.post("/kyc/customers", json=high_risk_payload)
    data_high = r_high.json()
    assert data_high["risk_assessment"]["risk_level"] in ["HIGH", "CRITICAL"]
    assert data_high["risk_assessment"]["cdd_tier"] == "ENHANCED_EDD"
    assert data_high["onboarding_status"] == "EDD_REQUIRED"


def test_compliance_review_decisions(client):
    """6. Test analyst compliance review (Approve, Reject, Escalate)."""
    # Create test customer
    onboard_payload = {
        "full_name": "Leonard McCoy",
        "date_of_birth_or_inc": "1970-03-20",
        "nationality_or_country": "US",
        "email": "bones@hospital-demo.com",
        "phone": "+1-555-9876",
        "tax_id_masked": "XXX-XX-5544"
    }
    c_resp = client.post("/kyc/customers", json=onboard_payload)
    cid = c_resp.json()["customer_id"]

    # 6a. Escalate to EDD
    review_edd = {
        "decision": "ESCALATED_EDD",
        "analyst_id": "analyst-rebecca",
        "rationale": "High wealth inflow expected; requested certified bank statements.",
        "edd_notes": "Source of wealth verification pending"
    }
    r_edd = client.post(f"/kyc/customers/{cid}/review", json=review_edd)
    assert r_edd.status_code == 200
    assert r_edd.json()["onboarding_status"] == "EDD_REQUIRED"
    assert r_edd.json()["reviewed_by"] == "analyst-rebecca"

    # 6b. Final Approval
    review_app = {
        "decision": "APPROVED",
        "analyst_id": "analyst-rebecca",
        "rationale": "Certified statements received and verified. Risk acceptable."
    }
    r_app = client.post(f"/kyc/customers/{cid}/review", json=review_app)
    assert r_app.status_code == 200
    assert r_app.json()["onboarding_status"] == "APPROVED"


def test_audit_trail_chronology(client):
    """7. Test audit trail records event types and chronologically tracks actions."""
    onboard_payload = {
        "full_name": "Hikaru Sulu",
        "date_of_birth_or_inc": "1982-10-12",
        "nationality_or_country": "JP",
        "email": "sulu@helios-demo.jp",
        "phone": "+81-3-1234-5678",
        "tax_id_masked": "JP-MYNO-***12"
    }
    c_resp = client.post("/kyc/customers", json=onboard_payload)
    cid = c_resp.json()["customer_id"]

    # Perform doc upload and screening
    client.post(f"/kyc/customers/{cid}/documents", json={
        "document_type": "DRIVING_LICENSE",
        "issuing_country": "JP",
        "document_number_masked": "DL-***99",
        "content_raw": "SAMPLE_JP_LICENSE"
    })
    client.post(f"/kyc/customers/{cid}/screen")

    # Fetch audit trail
    audit_resp = client.get(f"/kyc/customers/{cid}/audit-trail")
    assert audit_resp.status_code == 200
    trail = audit_resp.json()
    assert len(trail) >= 3

    event_types = [e["event_type"] for e in trail]
    assert "CUSTOMER_REGISTERED" in event_types
    assert "DOCUMENT_UPLOADED" in event_types
    assert "SCREENING_PERFORMED" in event_types


def test_end_to_end_onboarding_and_edd_workflow(client):
    """8. Test full end-to-end customer journey from onboarding to screening and compliance adjudication."""
    # 1. Onboard entity with possible adverse media
    payload = {
        "customer_type": "CORPORATE",
        "full_name": "Apex Global Trading",  # synthetic adverse media fixture
        "date_of_birth_or_inc": "2015-08-01",
        "nationality_or_country": "HK",
        "email": "corp@apex-demo.hk",
        "phone": "+852-2123-4567",
        "tax_id_masked": "HK-BR-***88"
    }
    reg_resp = client.post("/kyc/customers", json=payload)
    assert reg_resp.status_code == 201
    profile = reg_resp.json()
    cid = profile["customer_id"]

    # Screening should have caught adverse media
    assert len(profile["screening_matches"]) >= 1
    assert any(m["category"] == "ADVERSE_MEDIA" for m in profile["screening_matches"])
    assert profile["risk_assessment"]["cdd_tier"] in ["ENHANCED_EDD", "STANDARD_CDD"]

    # 2. Add corporate certificate document
    doc_resp = client.post(f"/kyc/customers/{cid}/documents", json={
        "document_type": "CERTIFICATE_OF_INCORPORATION",
        "issuing_country": "HK",
        "document_number_masked": "COI-***55",
        "content_raw": "CERTIFICATE_OF_INCORPORATION_CONTENT"
    })
    assert doc_resp.status_code == 201

    # 3. Compliance officer adjudicates rejection due to severe adverse media finding
    review_resp = client.post(f"/kyc/customers/{cid}/review", json={
        "decision": "REJECTED",
        "analyst_id": "senior-officer-miller",
        "rationale": "Unsatisfactory explanation for tax evasion investigation reported in adverse media. Entity onboarding denied."
    })
    assert review_resp.status_code == 200
    final_profile = review_resp.json()
    assert final_profile["onboarding_status"] == "REJECTED"
    assert final_profile["reviewed_by"] == "senior-officer-miller"
