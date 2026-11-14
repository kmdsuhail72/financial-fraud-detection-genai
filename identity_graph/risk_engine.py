"""
FinGuard AI — Phase 27: Synthetic Identity Risk Formulation & KYC Correlation
"""
from typing import List, Dict, Any, Set
from identity_graph.models import (
    SyntheticRiskTier,
    SyntheticIdentityRiskProfile,
    IdentityCollision,
    CollisionType,
)


class SyntheticRiskEngine:
    @staticmethod
    def assess_customer_risk(
        customer_id: str,
        collisions: List[IdentityCollision],
        kyc_status: str = "PENDING_REVIEW",
        doc_verification_status: str = "VERIFIED_AUTHENTIC_BYTES",
        cluster_size: int = 1
    ) -> SyntheticIdentityRiskProfile:
        score = 5.0
        risk_reasons: List[str] = []
        shared_attributes: List[str] = []
        colliding_customers: Set[str] = set()

        # 1. Collision Penalties
        for col in collisions:
            if customer_id in col.customer_ids:
                shared_attributes.append(f"{col.shared_attribute_type.value}: {col.shared_attribute_value}")
                for cid in col.customer_ids:
                    if cid != customer_id:
                        colliding_customers.add(cid)

                if col.collision_type == CollisionType.DOCUMENT_COLLISION:
                    score += 40.0
                    risk_reasons.append(f"DOCUMENT COLLISION: Identity document {col.shared_attribute_value} used by multiple profiles.")
                elif col.collision_type == CollisionType.DEVICE_COLLISION:
                    score += 25.0
                    risk_reasons.append(f"DEVICE COLLISION: Hardware device {col.shared_attribute_value} shared across accounts.")
                elif col.collision_type == CollisionType.PHONE_COLLISION:
                    score += 25.0
                    risk_reasons.append(f"PHONE COLLISION: Phone number {col.shared_attribute_value} linked to multiple identities.")
                elif col.collision_type == CollisionType.EMAIL_COLLISION:
                    score += 20.0
                    risk_reasons.append(f"EMAIL COLLISION: Email {col.shared_attribute_value} reused across accounts.")
                elif col.collision_type == CollisionType.ADDRESS_COLLISION:
                    score += 15.0
                    risk_reasons.append(f"ADDRESS COLLISION: Physical address {col.shared_attribute_value} shared with multiple applicants.")
                else:
                    score += 10.0
                    risk_reasons.append("Attribute collision detected with existing customer entity.")

        # 2. KYC Correlation (Phase 25)
        norm_kyc = (kyc_status or "").upper()
        if norm_kyc in {"EDD_REQUIRED", "REJECTED"}:
            score += 15.0
            risk_reasons.append(f"KYC Warning: Customer is flagged for {norm_kyc} in onboarding compliance.")

        # 3. Document Verification Correlation (Phase 26)
        norm_doc = (doc_verification_status or "").upper()
        if norm_doc in {"INCONSISTENT_FIELDS", "TAMPER_DETECTED"}:
            score += 25.0
            risk_reasons.append(f"Forensic Alert: Document verification flagged {norm_doc}.")

        # 4. Identity Ring Cluster Expansion
        if cluster_size >= 3:
            score += 15.0
            risk_reasons.append(f"Network Ring: Customer is part of a {cluster_size}-entity connected identity cluster.")

        final_score = min(100.0, max(0.0, round(score, 1)))

        # Assign Tier
        if final_score >= 80.0:
            tier = SyntheticRiskTier.CRITICAL
        elif final_score >= 60.0:
            tier = SyntheticRiskTier.HIGH
        elif final_score >= 30.0:
            tier = SyntheticRiskTier.MEDIUM
        else:
            tier = SyntheticRiskTier.LOW

        if not risk_reasons:
            risk_reasons.append("Clean identity footprint with no shared attribute collisions or forensic red flags.")

        return SyntheticIdentityRiskProfile(
            customer_id=customer_id,
            risk_score=final_score,
            risk_tier=tier,
            collision_count=len(shared_attributes),
            shared_attributes=shared_attributes,
            colliding_customers=sorted(list(colliding_customers)),
            risk_reasons=risk_reasons,
            kyc_correlation={
                "kyc_status": kyc_status,
                "doc_verification_status": doc_verification_status,
                "cluster_size": cluster_size
            }
        )

