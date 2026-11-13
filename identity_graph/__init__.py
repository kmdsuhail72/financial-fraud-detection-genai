"""
FinGuard AI — Phase 27: Synthetic Identity Fraud Detection & Identity Graph Intelligence
"""
from identity_graph.models import (
    NodeType,
    EdgeType,
    SyntheticRiskTier,
    CollisionType,
    InvestigationDecision,
    GraphNode,
    GraphEdge,
    IdentityCollision,
    SyntheticIdentityRiskProfile,
    IdentityRingCluster,
    CustomerIdentityRegistrationRequest,
    IdentityReviewRequest,
    IdentityAuditEvent,
)
from identity_graph.service import IdentityGraphService, get_identity_graph_service

__all__ = [
    "NodeType",
    "EdgeType",
    "SyntheticRiskTier",
    "CollisionType",
    "InvestigationDecision",
    "GraphNode",
    "GraphEdge",
    "IdentityCollision",
    "SyntheticIdentityRiskProfile",
    "IdentityRingCluster",
    "CustomerIdentityRegistrationRequest",
    "IdentityReviewRequest",
    "IdentityAuditEvent",
    "IdentityGraphService",
    "get_identity_graph_service",
]
