"""
FinGuard AI — Phase 28: Unified Customer Risk Intelligence Calculation Engine
Weighted multi-domain aggregation, signal coverage normalization, and explainability.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from customer_risk.models import (
    RiskDomain,
    DEFAULT_DOMAIN_WEIGHTS,
    CustomerRiskLevel,
    DomainSignal,
    CustomerRiskAssessment,
    CustomerAssessmentRequest,
    PreviousAssessmentComparison,
)

DEFAULT_SOURCES = {
    RiskDomain.KYC: "Phase 25 Customer Due Diligence (CDD/EDD) & Document Integrity",
    RiskDomain.AML: "Phase 24 AML Transaction Monitoring & Structuring Rules",
    RiskDomain.FRAUD: "Phases 1-21 ML Scoring & Multi-Signal Fusion Engine",
    RiskDomain.IDENTITY: "Phase 27 Synthetic Identity Detection & Attribute Collision Graph",
    RiskDomain.SANCTIONS: "Phase 25 Sanctions Watchlist Screening Engine",
    RiskDomain.PEP: "Phase 25 Politically Exposed Person (PEP) Registry",
    RiskDomain.BEHAVIORAL: "Phase 14 UEBA Behavioral Baseline & Velocity Deviations",
}


def classify_risk_level(score: float) -> CustomerRiskLevel:
    if score >= 75.0:
        return CustomerRiskLevel.CRITICAL
    elif score >= 50.0:
        return CustomerRiskLevel.HIGH
    elif score >= 25.0:
        return CustomerRiskLevel.MEDIUM
    return CustomerRiskLevel.LOW


class CustomerRiskEngine:
    @staticmethod
    def calculate_assessment(
        req: CustomerAssessmentRequest,
        previous_assessment: Optional[CustomerRiskAssessment] = None
    ) -> CustomerRiskAssessment:
        # 1. Collect provided domain scores
        provided_domains: Dict[RiskDomain, float] = {}
        if req.kyc_score is not None:
            provided_domains[RiskDomain.KYC] = float(req.kyc_score)
        if req.aml_score is not None:
            provided_domains[RiskDomain.AML] = float(req.aml_score)
        if req.fraud_score is not None:
            provided_domains[RiskDomain.FRAUD] = float(req.fraud_score)
        if req.identity_score is not None:
            provided_domains[RiskDomain.IDENTITY] = float(req.identity_score)
        if req.sanctions_score is not None:
            provided_domains[RiskDomain.SANCTIONS] = float(req.sanctions_score)
        if req.pep_score is not None:
            provided_domains[RiskDomain.PEP] = float(req.pep_score)
        if req.behavioral_score is not None:
            provided_domains[RiskDomain.BEHAVIORAL] = float(req.behavioral_score)

        if not provided_domains:
            # Fallback when no domains provided: evaluate at 0.0 with 0% coverage
            return CustomerRiskAssessment(
                assessment_id=f"ASSESS-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}",
                customer_id=req.customer_id,
                customer_name=req.customer_name,
                composite_risk_score=0.0,
                risk_level=CustomerRiskLevel.LOW,
                signal_coverage_percent=0.0,
                active_domains_count=0,
                domain_signals={},
                primary_risk_drivers=["No domain signals provided for assessment."],
                assessed_at=datetime.now(timezone.utc)
            )

        # 2. Compute Active Weight Sum & Signal Coverage
        active_weight_sum = sum(DEFAULT_DOMAIN_WEIGHTS[d] for d in provided_domains.keys())
        signal_coverage_pct = round(active_weight_sum * 100.0, 1)

        # 3. Renormalize weights & compute weighted contributions
        domain_signals: Dict[str, DomainSignal] = {}
        composite_score = 0.0
        primary_drivers: List[str] = []

        for domain, score in provided_domains.items():
            raw_w = DEFAULT_DOMAIN_WEIGHTS[domain]
            norm_w = raw_w / active_weight_sum
            contrib = round(norm_w * score, 2)
            composite_score += contrib

            user_src = req.sources.get(domain.value) if req.sources else None
            source_ref = user_src or DEFAULT_SOURCES.get(domain, "Internal Risk Model")

            user_ind = req.indicators.get(domain.value) if req.indicators else None
            ind_list = user_ind or [f"{domain.value} risk score evaluated at {score}/100."]

            sig = DomainSignal(
                domain=domain,
                score=score,
                raw_weight=raw_w,
                normalized_weight=round(norm_w, 4),
                weighted_contribution=contrib,
                source_reference=source_ref,
                indicators=ind_list
            )
            domain_signals[domain.value] = sig

            if score >= 50.0 or contrib >= 12.0:
                primary_drivers.append(f"{domain.value} (Score: {score:.1f}, Contribution: +{contrib:.1f} pts)")

        final_score = min(100.0, max(0.0, round(composite_score, 2)))
        risk_level = classify_risk_level(final_score)

        if not primary_drivers:
            primary_drivers.append("All active risk domains are operating within acceptable thresholds.")

        # 4. Compare with previous assessment if present (Reassessment Tracking)
        previous_comp: Optional[PreviousAssessmentComparison] = None
        if previous_assessment:
            delta = round(final_score - previous_assessment.composite_risk_score, 2)
            if delta > 0.5:
                direction = "INCREASED"
            elif delta < -0.5:
                direction = "DECREASED"
            else:
                direction = "STABLE"

            previous_comp = PreviousAssessmentComparison(
                previous_assessment_id=previous_assessment.assessment_id,
                previous_score=previous_assessment.composite_risk_score,
                previous_risk_level=previous_assessment.risk_level,
                score_delta=delta,
                direction=direction,
                assessed_at=previous_assessment.assessed_at
            )

        assessment = CustomerRiskAssessment(
            assessment_id=f"ASSESS-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}",
            customer_id=req.customer_id,
            customer_name=req.customer_name,
            composite_risk_score=final_score,
            risk_level=risk_level,
            signal_coverage_percent=signal_coverage_pct,
            active_domains_count=len(provided_domains),
            domain_signals=domain_signals,
            primary_risk_drivers=primary_drivers,
            previous_comparison=previous_comp,
            assessed_at=datetime.now(timezone.utc),
            notes=req.notes
        )

        return assessment

