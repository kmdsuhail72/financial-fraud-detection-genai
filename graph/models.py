"""Domain models and schemas for FinGuard AI Graph Analytics and Fraud Ring Detection."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NodeType(str, Enum):
    CUSTOMER = "CUSTOMER"
    ACCOUNT = "ACCOUNT"
    DEVICE = "DEVICE"
    IP_ADDRESS = "IP_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    MERCHANT = "MERCHANT"


class EdgeType(str, Enum):
    OWNS_ACCOUNT = "OWNS_ACCOUNT"
    USES_DEVICE = "USES_DEVICE"
    ASSOCIATED_IP = "ASSOCIATED_IP"
    HAS_PHONE = "HAS_PHONE"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    PAID_MERCHANT = "PAID_MERCHANT"


class RingRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GraphNode(BaseModel):
    """Represents a node (vertex) in the financial intelligence graph."""
    id: str = Field(..., description="Unique node identifier, e.g. CUS-1001, DEV-901, ACC-501")
    type: NodeType = Field(..., description="Entity classification")
    label: str = Field(..., description="Human-readable display name")
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Calculated graph risk score [0, 1]")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata attributes (e.g. OS, ASN, Balance)")

    model_config = ConfigDict(extra="allow")


class GraphEdge(BaseModel):
    """Represents a directed relationship (edge) between two nodes."""
    source: str = Field(..., description="Source node identifier")
    target: str = Field(..., description="Target node identifier")
    type: EdgeType = Field(..., description="Relationship semantic type")
    weight: float = Field(1.0, description="Edge weight (e.g. transfer amount or frequency)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge attributes (e.g. timestamp, transaction_id)")

    model_config = ConfigDict(extra="allow")


class SubgraphExport(BaseModel):
    """Ego-network subgraph payload for interactive frontend visualizers (D3, Cytoscape)."""
    center_node: str = Field(..., description="Queried root entity ID")
    depth_hops: int = Field(..., description="Neighborhood traversal radius")
    node_count: int = Field(...)
    edge_count: int = Field(...)
    nodes: List[GraphNode] = Field(default_factory=list)
    links: List[GraphEdge] = Field(default_factory=list)


class CentralityMetrics(BaseModel):
    """Graph centrality measurements for network prominence and flow analysis."""
    degree_centrality: float = 0.0
    in_degree_centrality: float = 0.0
    out_degree_centrality: float = 0.0
    pagerank: float = 0.0
    betweenness_centrality: float = 0.0
    in_degree: int = 0
    out_degree: int = 0


class CyclePath(BaseModel):
    """Represents a circular transfer pattern (wash trading or mule loop)."""
    cycle_id: str
    length: int
    nodes: List[str]
    total_amount: float
    description: str


class FraudRing(BaseModel):
    """Detected syndicate or cluster sharing critical infrastructure."""
    ring_id: str = Field(..., description="Unique identifier for the fraud syndicate")
    ring_name: str = Field(..., description="Descriptive ring label")
    risk_level: RingRiskLevel = Field(..., description="Threat classification")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Syndicate severity score")
    member_customers: List[str] = Field(default_factory=list, description="Customer IDs involved")
    member_accounts: List[str] = Field(default_factory=list, description="Account IDs involved")
    shared_devices: List[str] = Field(default_factory=list, description="Shared device fingerprints")
    shared_ips: List[str] = Field(default_factory=list, description="Shared IP addresses")
    shared_phones: List[str] = Field(default_factory=list, description="Shared phone numbers")
    total_flow_amount: float = Field(0.0, description="Aggregated transactional transfer amount")
    detected_patterns: List[str] = Field(default_factory=list, description="Indicators: e.g. SYNTHETIC_IDENTITY, MULE_LOOP")
    recommended_action: str = Field("FLAG_FOR_EXPEDITE_INVESTIGATION")


class EntityGraphScore(BaseModel):
    """Composite graph-based risk evaluation for an entity."""
    entity_id: str
    entity_type: NodeType
    graph_risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RingRiskLevel
    ring_membership: Optional[str] = None
    participating_cycles: List[str] = Field(default_factory=list)
    shared_entities_count: int = 0
    centrality: CentralityMetrics
    risk_factors: List[str] = Field(default_factory=list)


# =============================================================================
# Phase 16 — Real-Time Streaming & Neptune Enterprise Models
# =============================================================================
class CreateEntityRequest(BaseModel):
    id: str = Field(..., description="Unique entity identifier (e.g. CUS-1001, ACC-2001, DEV-801)")
    type: NodeType = Field(..., description="Entity vertex classification")
    label: Optional[str] = Field(None, description="Human-readable label")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata properties")

    model_config = ConfigDict(extra="allow")


class CreateRelationshipRequest(BaseModel):
    source: str = Field(..., description="Source vertex ID")
    target: str = Field(..., description="Target vertex ID")
    type: EdgeType = Field(..., description="Semantic edge type (e.g. OWNS_ACCOUNT, USES_DEVICE, TRANSFERRED_TO)")
    weight: float = Field(1.0, ge=0.0, description="Edge weight (e.g. amount or count)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties (timestamp, transaction_id)")

    model_config = ConfigDict(extra="allow")


class RiskEnrichmentRequest(BaseModel):
    transaction_id: str
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    merchant_id: Optional[str] = None
    amount: float = Field(0.0, ge=0.0)

    model_config = ConfigDict(extra="allow")


class RiskEnrichmentResponse(BaseModel):
    transaction_id: str
    graph_risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RingRiskLevel
    shared_device_customers_count: int = 0
    shared_ip_accounts_count: int = 0
    is_in_known_fraud_ring: bool = False
    circular_transfer_flag: bool = False
    inbound_velocity_ratio: float = 0.0
    network_risk_factors: List[str] = Field(default_factory=list)
    enriched_features: Dict[str, float] = Field(default_factory=dict)
    explanation: str

    model_config = ConfigDict(extra="allow")


class GraphAnalyzeRequest(BaseModel):
    entity_ids: Optional[List[str]] = Field(None, description="Optional root entity IDs to analyze")
    max_depth: int = Field(2, ge=1, le=4, description="Analysis traversal depth")


class GraphAnalyzeResponse(BaseModel):
    total_nodes: int
    total_edges: int
    connected_components: int
    fraud_rings_detected: int
    candidate_rings: List[FraudRing] = Field(default_factory=list)
    high_risk_entities: List[str] = Field(default_factory=list)
    summary: str


class NeptuneHealthResponse(BaseModel):
    status: str
    cluster_endpoint: str
    mode: str  # "AWS_NEPTUNE_LIVE" or "EMULATED_STANDALONE"
    vertex_count: int
    edge_count: int
    engine_version: str


# =============================================================================
# Phase 17 — Advanced Fraud Intelligence & Predictive Network Analytics
# =============================================================================
class CommunityCluster(BaseModel):
    """Detected topological community candidate with density & syndicate risk analysis."""
    community_id: str = Field(..., description="Unique identifier for detected community, e.g. COMM-01")
    members: List[str] = Field(default_factory=list, description="Entity node IDs belonging to this community")
    size: int = Field(..., ge=1, description="Total vertices in cluster")
    density: float = Field(0.0, ge=0.0, le=1.0, description="Internal subgraph edge density")
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Heuristic community risk score [0, 1]")
    risk_level: RingRiskLevel = Field(RingRiskLevel.LOW)
    has_shared_device: bool = False
    has_shared_ip: bool = False
    has_circular_loop: bool = False
    suspicious_indicators: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class PathAnalysisRequest(BaseModel):
    source_id: str = Field(..., description="Origin vertex ID")
    target_id: str = Field(..., description="Destination vertex ID")
    max_depth: int = Field(5, ge=1, le=8, description="Maximum traversal search depth")


class PathAnalysisResponse(BaseModel):
    source_id: str
    target_id: str
    path_exists: bool
    shortest_path_hops: int
    path_nodes: List[str] = Field(default_factory=list)
    path_relationships: List[str] = Field(default_factory=list)
    risk_summary: str

    model_config = ConfigDict(extra="allow")


class PredictiveNetworkRisk(BaseModel):
    """Advisory network-based predictive fraud risk evaluation for an entity."""
    entity_id: str
    pagerank: float = 0.0
    betweenness_centrality: float = 0.0
    degree_centrality: float = 0.0
    clustering_coefficient: float = 0.0
    community_id: Optional[str] = None
    community_risk_score: float = 0.0
    predictive_fraud_risk: float = Field(..., ge=0.0, le=1.0)
    advisory_risk_level: RingRiskLevel
    risk_factors: List[str] = Field(default_factory=list)
    recommendation: str

    model_config = ConfigDict(extra="allow")



