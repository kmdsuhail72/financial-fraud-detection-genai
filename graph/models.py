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

