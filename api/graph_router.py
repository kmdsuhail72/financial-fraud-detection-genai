"""FastAPI Router for Enterprise Graph Analytics, Real-Time Streaming & Fraud Intelligence (Phases 15 & 16)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from graph.graph_store import graph_store
from graph.advanced_analytics import get_advanced_analytics
from graph.models import (
    CommunityCluster,
    CreateEntityRequest,
    CreateRelationshipRequest,
    CyclePath,
    EntityGraphScore,
    FraudRing,
    GraphAnalyzeRequest,
    GraphAnalyzeResponse,
    GraphEdge,
    GraphNode,
    NeptuneHealthResponse,
    PathAnalysisRequest,
    PathAnalysisResponse,
    PredictiveNetworkRisk,
    RingRiskLevel,
    RiskEnrichmentRequest,
    RiskEnrichmentResponse,
    SubgraphExport,
)
from graph.neptune_client import get_neptune_client
from graph.neptune_queries import NeptuneQueryCatalog
from graph.scoring_adapter import GraphRiskEnricher
from security.auth import AuthenticatedUser
from security.audit import audit_logger
from security.dependencies import require_permission, require_roles
from security.roles import Permission, Role

graph_router = APIRouter(prefix="/graph", tags=["Enterprise Graph & Fraud Network Intelligence"])

neptune_client = get_neptune_client()
risk_enricher = GraphRiskEnricher(client=neptune_client)


class IngestGraphDataRequest(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# =============================================================================
# Phase 16 — Proposed Core Endpoints
# =============================================================================
@graph_router.get("/health", response_model=NeptuneHealthResponse)
def get_graph_health(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Probes Amazon Neptune / emulated Gremlin graph connectivity and element counts."""
    return neptune_client.health()


@graph_router.post("/entities", response_model=GraphNode, status_code=status.HTTP_201_CREATED)
def create_or_update_entity(
    payload: CreateEntityRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Creates or idempotently updates a vertex entity in the graph database."""
    node = neptune_client.upsert_vertex(
        vertex_id=payload.id,
        label=payload.type.value,
        properties=payload.properties,
        node_type=payload.type,
    )
    # Also keep graph_store synchronized
    graph_store.engine.g_full.add_node(
        payload.id,
        type=payload.type.value,
        label=payload.label or payload.id,
        **payload.properties,
    )

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="graph:create_entity",
        resource_type="VERTEX",
        resource_id=payload.id,
        status="SUCCESS",
        details={"type": payload.type.value},
    )
    return node


@graph_router.post("/relationships", response_model=GraphEdge, status_code=status.HTTP_201_CREATED)
def create_or_update_relationship(
    payload: CreateRelationshipRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Creates or idempotently updates a directed relationship edge between two entities."""
    edge = neptune_client.upsert_edge(
        source_id=payload.source,
        target_id=payload.target,
        edge_type=payload.type,
        weight=payload.weight,
        properties=payload.properties,
    )
    # Also sync into graph_store
    graph_store.engine.g_full.add_edge(
        payload.source,
        payload.target,
        type=payload.type.value,
        weight=payload.weight,
        **payload.properties,
    )

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="graph:create_relationship",
        resource_type="EDGE",
        resource_id=f"{payload.source}->{payload.target}",
        status="SUCCESS",
        details={"type": payload.type.value, "weight": payload.weight},
    )
    return edge


@graph_router.get("/entities/{entity_id}", response_model=GraphNode)
def get_entity_details(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves metadata and property details for a single entity vertex."""
    node = neptune_client.get_vertex(entity_id)
    if not node:
        # Check fallback graph_store
        if entity_id in graph_store.engine.g_full:
            d = graph_store.engine.g_full.nodes[entity_id]
            node = neptune_client.upsert_vertex(
                vertex_id=entity_id,
                label=d.get("type", "UNKNOWN"),
                properties=d,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found in graph database.",
            )
    return node


@graph_router.get("/entities/{entity_id}/neighbors", response_model=List[GraphNode])
def get_entity_neighbors(
    entity_id: str,
    direction: str = Query("both", pattern="^(in|out|both)$"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Finds all directly connected neighboring entities for a given vertex."""
    # Ensure entity exists
    get_entity_details(entity_id, current_user=current_user)
    neighbors = neptune_client.get_neighbors(entity_id, direction=direction)
    return neighbors


@graph_router.get("/entities/{entity_id}/network", response_model=SubgraphExport)
def traverse_entity_network(
    entity_id: str,
    depth: int = Query(2, ge=1, le=4, description="Graph traversal hops depth"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Traverses relationship paths up to depth hops to extract an ego-network."""
    # Seed from graph_store if not present in neptune_client
    if not neptune_client.get_vertex(entity_id) and entity_id in graph_store.engine.g_full:
        sub = graph_store.engine.extract_subgraph(center_id=entity_id, radius=depth)
        for n in sub.nodes:
            neptune_client.upsert_vertex(n.id, n.type.value, n.properties, n.type)
        for e in sub.links:
            neptune_client.upsert_edge(e.source, e.target, e.type, e.weight, e.properties)

    subgraph = neptune_client.get_network(root_id=entity_id, depth=depth)
    if subgraph.node_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in graph database.",
        )
    return subgraph


@graph_router.get("/fraud-rings", response_model=List[FraudRing])
def get_fraud_rings(
    risk_level: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves suspicious fraud network clusters and shared infrastructure rings."""
    rings = graph_store.engine.detect_fraud_rings()
    if risk_level:
        target = risk_level.upper()
        rings = [r for r in rings if r.risk_level.value == target]
    return rings


@graph_router.post("/risk-enrichment", response_model=RiskEnrichmentResponse)
def enrich_transaction_risk(
    request: RiskEnrichmentRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Generates graph-derived relationship features to enrich Phase 7 real-time fraud scoring."""
    response = risk_enricher.enrich(request)
    return response


@graph_router.post("/analyze", response_model=GraphAnalyzeResponse)
def analyze_graph_network(
    request: GraphAnalyzeRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Analyzes network connectivity, detects candidate fraud rings, and highlights high-risk clusters."""
    rings = graph_store.engine.detect_fraud_rings()
    cycles = graph_store.engine.detect_cycles(max_length=request.max_depth + 1)
    v_count, e_count = neptune_client.get_counts()

    high_risk: List[str] = []
    for r in rings:
        if r.risk_level in (RingRiskLevel.CRITICAL, RingRiskLevel.HIGH):
            high_risk.extend(r.member_customers)
            high_risk.extend(r.member_accounts)

    high_risk = sorted(list(set(high_risk)))

    summary = (
        f"Graph analysis evaluated {v_count} vertices and {e_count} edges across depth {request.max_depth}. "
        f"Identified {len(rings)} candidate fraud rings and {len(cycles)} circular flow paths."
    )

    return GraphAnalyzeResponse(
        total_nodes=v_count,
        total_edges=e_count,
        connected_components=max(1, len(rings)),
        fraud_rings_detected=len(rings),
        candidate_rings=rings,
        high_risk_entities=high_risk,
        summary=summary,
    )


# =============================================================================
# Phase 15 Compatibility Endpoints
# =============================================================================
@graph_router.get("/rings", response_model=List[FraudRing])
def list_fraud_rings(
    risk_level: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    return get_fraud_rings(risk_level=risk_level, current_user=current_user)


@graph_router.get("/rings/{ring_id}", response_model=FraudRing)
def get_fraud_ring(
    ring_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
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
    return traverse_entity_network(entity_id=entity_id, depth=radius, current_user=current_user)


@graph_router.get("/risk/{entity_id}", response_model=EntityGraphScore)
def get_entity_graph_risk(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
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
    cycles = graph_store.engine.detect_cycles(max_length=max_length)
    return cycles


@graph_router.get("/neptune/queries")
def get_neptune_queries(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    return {
        "gremlin": NeptuneQueryCatalog.get_gremlin_queries(),
        "opencypher": NeptuneQueryCatalog.get_opencypher_queries(),
    }


@graph_router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_graph_entities(
    payload: IngestGraphDataRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    graph_store.engine.ingest_batch(nodes=payload.nodes, edges=payload.edges)
    for n in payload.nodes:
        neptune_client.upsert_vertex(n.id, n.type.value, n.properties, n.type)
    for e in payload.edges:
        neptune_client.upsert_edge(e.source, e.target, e.type, e.weight, e.properties)

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


# =============================================================================
# Phase 17 — Advanced Fraud Intelligence & Predictive Network Analytics
# =============================================================================
analytics_suite = get_advanced_analytics()


@graph_router.get("/communities", response_model=List[CommunityCluster])
def list_network_communities(
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum community risk score threshold"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Detects suspicious communities and syndicates using Louvain topological modularity."""
    communities = analytics_suite.detect_communities()
    if min_risk is not None:
        communities = [c for c in communities if c.risk_score >= min_risk]
    return communities


@graph_router.get("/communities/{community_id}", response_model=CommunityCluster)
def get_community_cluster(
    community_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves deep topological analysis for a specific community cluster."""
    communities = analytics_suite.detect_communities()
    for c in communities:
        if c.community_id == community_id:
            return c
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Community '{community_id}' not found.")


@graph_router.get("/centrality/{entity_id}")
def get_entity_centrality(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Calculates Degree, Betweenness, and Closeness centrality for flow importance."""
    return analytics_suite.calculate_centrality(entity_id)


@graph_router.get("/pagerank")
def get_pagerank_rankings(
    limit: int = Query(25, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Ranks all network entities by PageRank authority flow score."""
    pr_scores = analytics_suite.calculate_pagerank()
    ranked = sorted(pr_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"entity_id": k, "pagerank": v} for k, v in ranked]


@graph_router.post("/paths/shortest", response_model=PathAnalysisResponse)
def analyze_shortest_path(
    request: PathAnalysisRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Analyzes shortest transaction and relationship routing paths between any two entities."""
    return analytics_suite.find_shortest_path(request)


@graph_router.post("/predict-risk", response_model=PredictiveNetworkRisk)
def predict_entity_network_risk(
    payload: Dict[str, str],
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Generates advisory predictive network risk index fusing centrality, PageRank, and community threat."""
    entity_id = payload.get("entity_id")
    if not entity_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Field 'entity_id' is required.")
    return analytics_suite.predict_entity_risk(entity_id)


@graph_router.post("/algorithms/run")
def execute_graph_algorithms_suite(
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Executes full Louvain, PageRank, and Betweenness suite across the entire graph."""
    communities = analytics_suite.detect_communities()
    pr_map = analytics_suite.calculate_pagerank()
    v_count, e_count = neptune_client.get_counts()

    top_pagerank = sorted(pr_map.items(), key=lambda x: x[1], reverse=True)[:5]
    high_risk_communities = [c for c in communities if c.risk_level in (RingRiskLevel.CRITICAL, RingRiskLevel.HIGH)]

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="graph:run_algorithms",
        resource_type="GRAPH",
        resource_id="full_network",
        status="SUCCESS",
        details={
            "communities_detected": len(communities),
            "high_risk_communities": len(high_risk_communities),
        },
    )

    return {
        "status": "COMPLETED",
        "total_vertices": v_count,
        "total_edges": e_count,
        "communities_count": len(communities),
        "high_risk_communities_count": len(high_risk_communities),
        "top_pagerank_entities": [{"id": k, "score": v} for k, v in top_pagerank],
    }
