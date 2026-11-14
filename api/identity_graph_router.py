"""
FinGuard AI — Phase 27: Synthetic Identity & Identity Graph API Router
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from identity_graph.models import (
    CustomerIdentityRegistrationRequest,
    SyntheticIdentityRiskProfile,
    IdentityCollision,
    IdentityRingCluster,
    IdentityReviewRequest,
    IdentityAuditEvent,
    SubgraphResponse,
)
from identity_graph.service import get_identity_graph_service

identity_graph_router = APIRouter(prefix="/identity/graph", tags=["Synthetic Identity & Identity Graph Intelligence"])


@identity_graph_router.get("/health")
def identity_graph_health():
    """Health check for identity graph and synthetic fraud detection service."""
    return {
        "status": "ok",
        "service": "identity_graph",
        "version": "1.0.0"
    }


@identity_graph_router.post("/register", response_model=SyntheticIdentityRiskProfile, status_code=status.HTTP_201_CREATED)
def register_identity(req: CustomerIdentityRegistrationRequest):
    """
    Registers a customer identity and attributes (phone, email, device, IP, address, doc)
    into the identity graph, evaluating real-time collisions and synthetic risk.
    """
    try:
        service = get_identity_graph_service()
        return service.register_customer_identity(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@identity_graph_router.get("/subgraph", response_model=SubgraphResponse)
def get_identity_subgraph(
    customer_id: Optional[str] = Query(None, description="Optional center customer ID for ego network"),
    max_depth: int = Query(2, ge=1, le=4, description="Graph traversal hop depth")
):
    """Retrieves identity network nodes and edges for visual graph exploration."""
    service = get_identity_graph_service()
    return service.get_subgraph(customer_id=customer_id, max_depth=max_depth)


@identity_graph_router.get("/collisions", response_model=List[IdentityCollision])
def list_identity_collisions(
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)")
):
    """Lists detected identity collisions across phones, emails, devices, and addresses."""
    service = get_identity_graph_service()
    return service.get_collisions(severity=severity)


@identity_graph_router.get("/clusters", response_model=List[IdentityRingCluster])
def list_identity_ring_clusters():
    """Identifies connected identity ring clusters and multi-applicant synthetic rings."""
    service = get_identity_graph_service()
    return service.get_clusters()


@identity_graph_router.get("/customers/{customer_id}/risk", response_model=SyntheticIdentityRiskProfile)
def get_customer_synthetic_risk(customer_id: str):
    """Retrieves explainable synthetic identity risk profile, collision details, and KYC correlation."""
    service = get_identity_graph_service()
    c_node = service.store.graph_engine.get_node(customer_id)
    if not c_node:
        raise HTTPException(status_code=404, detail=f"Customer identity '{customer_id}' not found in graph")
    return service.get_customer_risk_profile(customer_id)


@identity_graph_router.post("/customers/{customer_id}/review", response_model=SyntheticIdentityRiskProfile)
def review_customer_identity(customer_id: str, req: IdentityReviewRequest):
    """Submits formal analyst adjudication (Flag Ring, Clear Collision, Request EDD)."""
    try:
        service = get_identity_graph_service()
        c_node = service.store.graph_engine.get_node(customer_id)
        if not c_node:
            raise HTTPException(status_code=404, detail=f"Customer identity '{customer_id}' not found in graph")
        return service.review_identity(customer_id=customer_id, req=req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@identity_graph_router.get("/customers/{customer_id}/audit-trail", response_model=List[IdentityAuditEvent])
def get_identity_audit_trail(customer_id: str):
    """Retrieves chronological audit events for identity registration, collision detections, and reviews."""
    service = get_identity_graph_service()
    c_node = service.store.graph_engine.get_node(customer_id)
    if not c_node:
        raise HTTPException(status_code=404, detail=f"Customer identity '{customer_id}' not found in graph")
    return service.get_audit_trail(customer_id)

