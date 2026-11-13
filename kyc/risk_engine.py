"""
FinGuard AI — Phase 25: Customer Risk Profiling & CDD/EDD Evaluation Engine
"""
from typing import List
from kyc.models import (
    CustomerType,
    RiskLevel,
    CDDTier,
    ScreeningMatch,
    ScreeningMatchCategory,
    KYCDocument,
    CustomerRiskAssessment,
)

# High-risk jurisdiction list (FATF Call for Action & Increased Monitoring style)
HIGH_RISK_JURISDICTIONS = {"KP", "IR", "MM", "SY", "CU", "YE"}
MEDIUM_RISK_JURISDICTIONS = {"KY", "PA", "VG", "CY", "AE"}


class CustomerRiskEngine:
    """
    Computes explainable Customer Due Diligence (CDD) and Enhanced Due Diligence (EDD) tiers.
    Score ranges from 0 to 100.
    """

    @staticmethod
    def assess_risk(
        customer_type: CustomerType,
        nationality_or_country: str,
        documents: List[KYCDocument],
        screening_matches: List[ScreeningMatch]
    ) -> CustomerRiskAssessment:
        score = 10.0  # Baseline low customer risk
        risk_factors: List[str] = []

        # 1. Customer Type factor
        if customer_type == CustomerType.CORPORATE:
            score += 10.0
            risk_factors.append("Corporate Entity (requires beneficial ownership verification)")

        # 2. Geographic / Jurisdiction Risk
        norm_country = nationality_or_country.upper().strip()
        if norm_country in HIGH_RISK_JURISDICTIONS:
            score += 35.0
            risk_factors.append(f"High-Risk Jurisdiction affiliation ({norm_country})")
        elif norm_country in MEDIUM_RISK_JURISDICTIONS:
            score += 15.0
            risk_factors.append(f"Offshore / Monitored Jurisdiction affiliation ({norm_country})")

        # 3. Document Verification status
        if not documents:
            score += 20.0
            risk_factors.append("No verified KYC documents attached")
        else:
            has_government_id = any(
                doc.document_type.value in {"PASSPORT", "NATIONAL_ID", "DRIVING_LICENSE"}
                for doc in documents
            )
            if not has_government_id:
                score += 15.0
                risk_factors.append("Missing primary government-issued photo identification")

        # 4. Screening Matches (PEP, Sanctions, Adverse Media)
        has_sanctions = False
        has_pep = False
        has_adverse = False

        for match in screening_matches:
            if match.category == ScreeningMatchCategory.SANCTIONS:
                has_sanctions = True
                score += 50.0
                risk_factors.append(f"Sanctions Match detected: '{match.matched_entity_name}' (conf: {match.match_confidence.value})")
            elif match.category == ScreeningMatchCategory.PEP:
                has_pep = True
                score += 35.0
                risk_factors.append(f"Politically Exposed Person (PEP) match: '{match.matched_entity_name}' (conf: {match.match_confidence.value})")
            elif match.category == ScreeningMatchCategory.ADVERSE_MEDIA:
                has_adverse = True
                score += 20.0
                risk_factors.append(f"Adverse Media identified: '{match.matched_entity_name}'")

        # Cap score between 0.0 and 100.0
        final_score = min(100.0, max(0.0, round(score, 1)))

        # Determine Tier and Risk Level
        if has_sanctions or final_score >= 80.0:
            risk_level = RiskLevel.CRITICAL
            cdd_tier = CDDTier.ENHANCED_EDD
            explanation = "CRITICAL RISK: Direct sanctions hit or extreme risk indicators. Mandatory EDD and Senior Compliance Officer review required."
        elif has_pep or final_score >= 55.0:
            risk_level = RiskLevel.HIGH
            cdd_tier = CDDTier.ENHANCED_EDD
            explanation = "HIGH RISK: PEP match, high-risk jurisdiction, or elevated compounding factors. Enhanced Due Diligence (EDD) required."
        elif final_score >= 30.0:
            risk_level = RiskLevel.MEDIUM
            cdd_tier = CDDTier.STANDARD_CDD
            explanation = "MEDIUM RISK: Standard Customer Due Diligence (CDD) applicable. No active sanctions or PEP flags."
        else:
            risk_level = RiskLevel.LOW
            cdd_tier = CDDTier.SIMPLIFIED_SDD
            explanation = "LOW RISK: Simplified Due Diligence (SDD) eligible. Verified documents and clean screening profile."

        return CustomerRiskAssessment(
            risk_level=risk_level,
            score=final_score,
            risk_factors=risk_factors,
            cdd_tier=cdd_tier,
            explanation=explanation
        )

