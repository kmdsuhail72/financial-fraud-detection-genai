"""FastAPI Router for Enterprise Graph Analytics and Fraud Ring Detection (Phase 15)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from graph.graph_store import graph_store
from graph.models import (
    CyclePath,
    EntityGraphScore,
    FraudRing,
    GraphEdge,
    GraphNode,
    RingRiskLevel,
    SubgraphExport,
)
from graph.neptune_queries import NeptuneQueryCatalog
from security.auth import AuthenticatedUser
from security.audit import audit_logger
from security.dependencies import require_permission, require_roles
from security.roles import Permission, Role

graph_router = APIRouter(prefix="/graph", tags=["Graph Analytics & Fraud Ring Intelligence"])


class IngestGraphDataRequest(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


@graph_router.get("/rings", response_model=List[FraudRing])
def list_fraud_rings(
    risk_level: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Lists detected fraud rings and synthetic identity syndicates. Requires 'cases:view'."""
    rings = graph_store.engine.detect_fraud_rings()
    if risk_level:
        target = risk_level.upper()
        rings = [r for r in rings if r.risk_level.value == target]
    return rings


@graph_router.get("/rings/{ring_id}", response_model=FraudRing)
def get_fraud_ring(
    ring_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves detailed intelligence on a specific fraud ring cluster."""
    rings = graph_store.engine.detect_fraud_rings()
    for r in rings:
        if r.ring_id == ring_id:
            return r
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fraud ring '{ring_id}' not found.")


@graph_router.get("/entity/{entity_id}/subgraph", response_model=SubgraphExport)
def get_entity_subgraph(
    entity_id: str,
    radius: int = Query(2, ge=1, le=3, description="Neighborhood traversal radius hops"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves k-hop ego-network for interactive visualization and investigation dossiers."""
    try:
        subgraph = graph_store.engine.extract_subgraph(center_id=entity_id, radius=radius)
        return subgraph
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in fraud intelligence graph.",
        )


@graph_router.get("/risk/{entity_id}", response_model=EntityGraphScore)
def get_entity_graph_risk(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Calculates network centrality, ring participation, circular flows, and composite Graph Risk Score."""
    try:
        score = graph_store.engine.calculate_entity_risk(entity_id=entity_id)
        return score
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in fraud intelligence graph.",
        )


@graph_router.get("/cycles", response_model=List[CyclePath])
def list_circular_transfer_loops(
    max_length: int = Query(6, ge=2, le=10, description="Maximum cycle length"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Detects closed circular fund loops (wash trading and money mule cycles)."""
    cycles = graph_store.engine.detect_cycles(max_length=max_length)
    return cycles


@graph_router.get("/neptune/queries")
def get_neptune_queries(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Returns pre-compiled Gremlin and openCypher queries for Amazon Neptune production clusters."""
    return {
        "gremlin": NeptuneQueryCatalog.get_gremlin_queries(),
        "opencypher": NeptuneQueryCatalog.get_opencypher_queries(),
    }


@graph_router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_graph_entities(
    payload: IngestGraphDataRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Ingests new nodes and edges into the live graph. Requires Investigator or Admin role."""
    graph_store.engine.ingest_batch(nodes=payload.nodes, edges=payload.edges)
    
    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="graph:ingest_data",
        resource_type="GRAPH",
        resource_id=f"batch-{len(payload.nodes)}n-{len(payload.edges)}e",
        status="SUCCESS",
        details={"nodes_added": len(payload.nodes), "edges_added": len(payload.edges)},
    )

    return {
        "status": "SUCCESS",
        "nodes_ingested": len(payload.nodes),
        "edges_ingested": len(payload.edges),
        "total_nodes": graph_store.engine.g_full.number_of_nodes(),
        "total_edges": graph_store.engine.g_full.number_of_edges(),
    }
