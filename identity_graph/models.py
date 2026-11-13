"""
FinGuard AI — Phase 27: Synthetic Identity & Identity Graph Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    CUSTOMER = "CUSTOMER"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    DEVICE = "DEVICE"
    IP = "IP"
    ADDRESS = "ADDRESS"
    DOCUMENT = "DOCUMENT"


class EdgeType(str, Enum):
    OWNS_PHONE = "OWNS_PHONE"
    USES_EMAIL = "USES_EMAIL"
    OPERATES_DEVICE = "OPERATES_DEVICE"
    ORIGINATES_IP = "ORIGINATES_IP"
    RESIDES_ADDRESS = "RESIDES_ADDRESS"
    HOLDS_DOCUMENT = "HOLDS_DOCUMENT"
    COLLIDES_WITH = "COLLIDES_WITH"


class SyntheticRiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CollisionType(str, Enum):
    PHONE_COLLISION = "PHONE_COLLISION"
    EMAIL_COLLISION = "EMAIL_COLLISION"
    DEVICE_COLLISION = "DEVICE_COLLISION"
    ADDRESS_COLLISION = "ADDRESS_COLLISION"
    DOCUMENT_COLLISION = "DOCUMENT_COLLISION"
    MULTI_ATTRIBUTE_COLLISION = "MULTI_ATTRIBUTE_COLLISION"


class InvestigationDecision(str, Enum):
    FLAG_SYNTHETIC_RING = "FLAG_SYNTHETIC_RING"
    CLEAR_COLLISION = "CLEAR_COLLISION"
    REQUEST_EDD = "REQUEST_EDD"
    UNDER_REVIEW = "UNDER_REVIEW"


class GraphNode(BaseModel):
    node_id: str = Field(..., description="Unique node ID (e.g. CUST-101, PHONE-+1555..., DEV-XYZ)")
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=1.0)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdentityCollision(BaseModel):
    collision_id: str
    collision_type: CollisionType
    shared_attribute_type: NodeType
    shared_attribute_value: str
    customer_ids: List[str]
    severity: SyntheticRiskTier
    collision_score: float = Field(..., ge=0.0, le=100.0)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class SyntheticIdentityRiskProfile(BaseModel):
    customer_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: SyntheticRiskTier
    collision_count: int
    shared_attributes: List[str] = Field(default_factory=list)
    colliding_customers: List[str] = Field(default_factory=list)
    risk_reasons: List[str] = Field(default_factory=list)
    kyc_correlation: Dict[str, Any] = Field(default_factory=dict)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdentityRingCluster(BaseModel):
    cluster_id: str
    customer_count: int
    customer_ids: List[str]
    entity_nodes_count: int
    shared_attributes_summary: List[str]
    cluster_risk_score: float = Field(..., ge=0.0, le=100.0)
    cluster_risk_tier: SyntheticRiskTier
    status: InvestigationDecision = Field(default=InvestigationDecision.UNDER_REVIEW)


class CustomerIdentityRegistrationRequest(BaseModel):
    customer_id: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    document_id: Optional[str] = None
    kyc_status: Optional[str] = "PENDING_REVIEW"
    doc_verification_status: Optional[str] = "VERIFIED_AUTHENTIC_BYTES"


class IdentityReviewRequest(BaseModel):
    analyst_id: str
    decision: InvestigationDecision
    rationale: str
    escalate_to_sar: bool = False


class IdentityAuditEvent(BaseModel):
    event_id: str
    customer_id: str
    event_type: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class SubgraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int
