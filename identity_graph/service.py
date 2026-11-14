"""
FinGuard AI — Phase 27: Identity Graph Orchestration Service
"""
from typing import List, Optional, Dict, Any
from identity_graph.models import (
    CustomerIdentityRegistrationRequest,
    SyntheticIdentityRiskProfile,
    IdentityCollision,
    IdentityRingCluster,
    IdentityReviewRequest,
    IdentityAuditEvent,
    SubgraphResponse,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType,
    InvestigationDecision,
)
from identity_graph.store import IdentityGraphStore, get_identity_graph_store
from identity_graph.risk_engine import SyntheticRiskEngine


class IdentityGraphService:
    def __init__(self, store: Optional[IdentityGraphStore] = None):
        self.store = store or get_identity_graph_store()
        self.risk_engine = SyntheticRiskEngine()

    def register_customer_identity(
        self,
        req: CustomerIdentityRegistrationRequest,
        actor: str = "identity-service"
    ) -> SyntheticIdentityRiskProfile:
        with self.store._lock:
            self.store._add_customer_identity_internal(
                customer_id=req.customer_id,
                full_name=req.full_name,
                phone=req.phone,
                email=req.email,
                address=req.address,
                device_id=req.device_id,
                ip_address=req.ip_address,
                document_id=req.document_id,
                kyc_status=req.kyc_status or "PENDING_REVIEW",
                doc_verification_status=req.doc_verification_status or "VERIFIED_AUTHENTIC_BYTES"
            )

        # Assess risk profile immediately
        profile = self.get_customer_risk_profile(
            customer_id=req.customer_id,
            kyc_status=req.kyc_status or "PENDING_REVIEW",
            doc_verification_status=req.doc_verification_status or "VERIFIED_AUTHENTIC_BYTES"
        )
        return profile

    def get_subgraph(self, customer_id: Optional[str] = None, max_depth: int = 2) -> SubgraphResponse:
        nodes, edges = self.store.graph_engine.get_subgraph(root_id=customer_id, max_depth=max_depth)
        return SubgraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )

    def get_collisions(self, severity: Optional[str] = None) -> List[IdentityCollision]:
        collisions = self.store.graph_engine.detect_collisions()
        if severity:
            collisions = [c for c in collisions if c.severity.value == severity.upper()]
        return collisions

    def get_clusters(self) -> List[IdentityRingCluster]:
        return self.store.graph_engine.find_identity_ring_clusters()

    def get_customer_risk_profile(
        self,
        customer_id: str,
        kyc_status: Optional[str] = None,
        doc_verification_status: Optional[str] = None
    ) -> SyntheticIdentityRiskProfile:
        collisions = self.get_collisions()
        clusters = self.get_clusters()

        # Find cluster size
        cluster_size = 1
        for cl in clusters:
            if customer_id in cl.customer_ids:
                cluster_size = cl.customer_count
                break

        # If not provided, fetch node properties
        c_node = self.store.graph_engine.get_node(customer_id)
        if c_node:
            resolved_kyc = kyc_status or c_node.properties.get("kyc_status", "PENDING_REVIEW")
            resolved_doc = doc_verification_status or c_node.properties.get("doc_verification_status", "VERIFIED_AUTHENTIC_BYTES")
        else:
            resolved_kyc = kyc_status or "PENDING_REVIEW"
            resolved_doc = doc_verification_status or "VERIFIED_AUTHENTIC_BYTES"

        profile = self.risk_engine.assess_customer_risk(
            customer_id=customer_id,
            collisions=collisions,
            kyc_status=resolved_kyc,
            doc_verification_status=resolved_doc,
            cluster_size=cluster_size
        )
        self.store._risk_profiles[customer_id] = profile
        return profile

    def review_identity(self, customer_id: str, req: IdentityReviewRequest) -> SyntheticIdentityRiskProfile:
        profile = self.get_customer_risk_profile(customer_id)
        
        self.store._customer_reviews[customer_id] = {
            "analyst_id": req.analyst_id,
            "decision": req.decision.value,
            "rationale": req.rationale,
            "escalate_to_sar": req.escalate_to_sar
        }

        # Update node status in graph if flagged
        c_node = self.store.graph_engine.get_node(customer_id)
        if c_node:
            c_node.properties["investigation_status"] = req.decision.value

        self.store.log_audit(
            customer_id=customer_id,
            event_type="IDENTITY_INVESTIGATION_DECIDED",
            actor=req.analyst_id,
            details={
                "decision": req.decision.value,
                "rationale": req.rationale,
                "escalate_to_sar": req.escalate_to_sar
            }
        )

        return profile

    def get_audit_trail(self, customer_id: str) -> List[IdentityAuditEvent]:
        return self.store.get_audit_trail(customer_id)


# Global singleton service
_identity_graph_service = IdentityGraphService()


def get_identity_graph_service() -> IdentityGraphService:
    return _identity_graph_service

