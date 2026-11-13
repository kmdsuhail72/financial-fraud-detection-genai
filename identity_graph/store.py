"""
FinGuard AI — Phase 27: Identity Graph Store & Seeded Synthetic Ring
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from identity_graph.models import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge,
    IdentityCollision,
    SyntheticIdentityRiskProfile,
    IdentityRingCluster,
    IdentityAuditEvent,
    InvestigationDecision,
)
from identity_graph.graph_engine import IdentityGraphEngine
from identity_graph.risk_engine import SyntheticRiskEngine


class IdentityGraphStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.graph_engine = IdentityGraphEngine()
        self._risk_profiles: Dict[str, SyntheticIdentityRiskProfile] = {}
        self._customer_reviews: Dict[str, Dict] = {}
        self._audit_trail: Dict[str, List[IdentityAuditEvent]] = {}
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Seed realistic clean customers and a planted synthetic identity fraud ring."""
        # 1. Clean Customer (Sarah Connor)
        c1_id = "CUST-US-9011"
        self._add_customer_identity_internal(
            customer_id=c1_id,
            full_name="Sarah Connor",
            phone="+1-555-0199",
            email="sarah.c@techcorp-demo.com",
            address="1200 Sunset Blvd, Los Angeles, CA",
            device_id="DEV-IOS-9011",
            ip_address="198.51.100.44",
            document_id="DOC-9011-PASS",
            kyc_status="APPROVED",
            doc_verification_status="VERIFIED_AUTHENTIC_BYTES"
        )

        # 2. Planted Synthetic Identity Ring (3 colliding applicants sharing phone, address, and device)
        ring_phone = "+1-555-8888"
        ring_address = "742 Evergreen Terr, Springfield, OR"
        ring_device = "DEV-ANDROID-EMU-01"

        c2_id = "CUST-SYN-001"
        self._add_customer_identity_internal(
            customer_id=c2_id,
            full_name="Alex Mercer",
            phone=ring_phone,
            email="alex.m@ghostmail-demo.com",
            address=ring_address,
            device_id=ring_device,
            ip_address="203.0.113.88",
            document_id="DOC-SYN-001",
            kyc_status="PENDING_REVIEW",
            doc_verification_status="VERIFIED_AUTHENTIC_BYTES"
        )

        c3_id = "CUST-SYN-002"
        self._add_customer_identity_internal(
            customer_id=c3_id,
            full_name="Alexander J. Mercer",
            phone=ring_phone,  # COLLISION
            email="amercer99@tempinbox-demo.com",
            address=ring_address,  # COLLISION
            device_id=ring_device,  # COLLISION
            ip_address="203.0.113.88",
            document_id="DOC-SYN-002",
            kyc_status="EDD_REQUIRED",
            doc_verification_status="INCONSISTENT_FIELDS"
        )

        c4_id = "CUST-SYN-003"
        self._add_customer_identity_internal(
            customer_id=c4_id,
            full_name="A. Mercer Holdings",
            phone=ring_phone,  # COLLISION
            email="contact@mercer-shell-demo.com",
            address=ring_address,  # COLLISION
            device_id=ring_device,  # COLLISION
            ip_address="203.0.113.88",
            document_id="DOC-SYN-003",
            kyc_status="EDD_REQUIRED",
            doc_verification_status="VERIFIED_AUTHENTIC_BYTES"
        )

    def _add_customer_identity_internal(
        self,
        customer_id: str,
        full_name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        document_id: Optional[str] = None,
        kyc_status: str = "PENDING_REVIEW",
        doc_verification_status: str = "VERIFIED_AUTHENTIC_BYTES"
    ):
        # 1. Add Customer Node
        c_node = GraphNode(
            node_id=customer_id,
            node_type=NodeType.CUSTOMER,
            label=full_name,
            properties={
                "full_name": full_name,
                "kyc_status": kyc_status,
                "doc_verification_status": doc_verification_status
            }
        )
        self.graph_engine.add_node(c_node)

        # 2. Add Attribute Nodes & Edges
        if phone:
            p_node_id = f"PHONE-{phone}"
            if not self.graph_engine.get_node(p_node_id):
                self.graph_engine.add_node(GraphNode(node_id=p_node_id, node_type=NodeType.PHONE, label=phone))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=p_node_id, edge_type=EdgeType.OWNS_PHONE))

        if email:
            e_node_id = f"EMAIL-{email}"
            if not self.graph_engine.get_node(e_node_id):
                self.graph_engine.add_node(GraphNode(node_id=e_node_id, node_type=NodeType.EMAIL, label=email))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=e_node_id, edge_type=EdgeType.USES_EMAIL))

        if address:
            a_node_id = f"ADDR-{address}"
            if not self.graph_engine.get_node(a_node_id):
                self.graph_engine.add_node(GraphNode(node_id=a_node_id, node_type=NodeType.ADDRESS, label=address))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=a_node_id, edge_type=EdgeType.RESIDES_ADDRESS))

        if device_id:
            d_node_id = f"DEV-{device_id}"
            if not self.graph_engine.get_node(d_node_id):
                self.graph_engine.add_node(GraphNode(node_id=d_node_id, node_type=NodeType.DEVICE, label=device_id))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=d_node_id, edge_type=EdgeType.OPERATES_DEVICE))

        if ip_address:
            ip_node_id = f"IP-{ip_address}"
            if not self.graph_engine.get_node(ip_node_id):
                self.graph_engine.add_node(GraphNode(node_id=ip_node_id, node_type=NodeType.IP, label=ip_address))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=ip_node_id, edge_type=EdgeType.ORIGINATES_IP))

        if document_id:
            doc_node_id = f"DOC-{document_id}"
            if not self.graph_engine.get_node(doc_node_id):
                self.graph_engine.add_node(GraphNode(node_id=doc_node_id, node_type=NodeType.DOCUMENT, label=document_id))
            self.graph_engine.add_edge(GraphEdge(source_id=customer_id, target_id=doc_node_id, edge_type=EdgeType.HOLDS_DOCUMENT))

        # Log audit
        self._log_audit_internal(
            customer_id=customer_id,
            event_type="IDENTITY_ATTRIBUTES_INGESTED",
            actor="system",
            details={"full_name": full_name, "kyc_status": kyc_status}
        )

    def _log_audit_internal(self, customer_id: str, event_type: str, actor: str, details: Dict):
        event = IdentityAuditEvent(
            event_id=f"ID-AUD-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            event_type=event_type,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
        if customer_id not in self._audit_trail:
            self._audit_trail[customer_id] = []
        self._audit_trail[customer_id].append(event)

    def log_audit(self, customer_id: str, event_type: str, actor: str, details: Dict) -> IdentityAuditEvent:
        with self._lock:
            event = IdentityAuditEvent(
                event_id=f"ID-AUD-{uuid.uuid4().hex[:8].upper()}",
                customer_id=customer_id,
                event_type=event_type,
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                details=details
            )
            if customer_id not in self._audit_trail:
                self._audit_trail[customer_id] = []
            self._audit_trail[customer_id].append(event)
            return event

    def get_audit_trail(self, customer_id: str) -> List[IdentityAuditEvent]:
        with self._lock:
            return sorted(
                self._audit_trail.get(customer_id, []),
                key=lambda e: e.timestamp,
                reverse=True
            )


# Global singleton instance
_identity_graph_store = IdentityGraphStore()


def get_identity_graph_store() -> IdentityGraphStore:
    return _identity_graph_store
