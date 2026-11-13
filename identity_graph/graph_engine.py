"""
FinGuard AI — Phase 27: In-Memory Identity Graph & Network Engine
Pure Python graph traversal with NetworkX compatibility for relationship analysis.
"""
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple, Any
from identity_graph.models import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge,
    IdentityCollision,
    CollisionType,
    SyntheticRiskTier,
    IdentityRingCluster,
    InvestigationDecision,
)


class IdentityGraphEngine:
    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._customer_to_entities: Dict[str, Set[str]] = defaultdict(set)
        self._entity_to_customers: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: GraphNode) -> GraphNode:
        self._nodes[node.node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        self._edges.append(edge)
        self._adjacency[edge.source_id].add(edge.target_id)
        self._adjacency[edge.target_id].add(edge.source_id)

        # Track bipartite relationship between CUSTOMER and Entity attributes
        source_node = self._nodes.get(edge.source_id)
        target_node = self._nodes.get(edge.target_id)

        if source_node and target_node:
            if source_node.node_type == NodeType.CUSTOMER and target_node.node_type != NodeType.CUSTOMER:
                self._customer_to_entities[source_node.node_id].add(target_node.node_id)
                self._entity_to_customers[target_node.node_id].add(source_node.node_id)
            elif target_node.node_type == NodeType.CUSTOMER and source_node.node_type != NodeType.CUSTOMER:
                self._customer_to_entities[target_node.node_id].add(source_node.node_id)
                self._entity_to_customers[source_node.node_id].add(target_node.node_id)

        return edge

    def get_subgraph(self, root_id: Optional[str] = None, max_depth: int = 2) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Extracts a localized ego network around root_id via BFS up to max_depth.
        If root_id is None, returns the entire graph up to 150 nodes.
        """
        if not root_id or root_id not in self._nodes:
            # Return full graph (or first 150 nodes)
            nodes = list(self._nodes.values())[:150]
            node_ids = {n.node_id for n in nodes}
            edges = [e for e in self._edges if e.source_id in node_ids and e.target_id in node_ids]
            return nodes, edges

        visited_ids: Set[str] = {root_id}
        queue = deque([(root_id, 0)])

        while queue:
            curr_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            for neighbor_id in self._adjacency.get(curr_id, set()):
                if neighbor_id not in visited_ids:
                    visited_ids.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

        nodes = [self._nodes[nid] for nid in visited_ids if nid in self._nodes]
        edges = [e for e in self._edges if e.source_id in visited_ids and e.target_id in visited_ids]
        return nodes, edges

    def detect_collisions(self) -> List[IdentityCollision]:
        """
        Scans all entity nodes (Phone, Email, Device, Address, Document, IP)
        and detects when an entity is linked to 2 or more distinct customer IDs.
        """
        collisions: List[IdentityCollision] = []

        for entity_id, customer_ids in self._entity_to_customers.items():
            if len(customer_ids) >= 2:
                entity_node = self._nodes.get(entity_id)
                if not entity_node:
                    continue

                ntype = entity_node.node_type
                c_list = sorted(list(customer_ids))

                # Determine collision type and severity
                if ntype == NodeType.DOCUMENT:
                    ctype = CollisionType.DOCUMENT_COLLISION
                    severity = SyntheticRiskTier.CRITICAL
                    base_score = 90.0
                elif ntype == NodeType.DEVICE:
                    ctype = CollisionType.DEVICE_COLLISION
                    severity = SyntheticRiskTier.HIGH if len(c_list) >= 3 else SyntheticRiskTier.MEDIUM
                    base_score = 75.0 if len(c_list) >= 3 else 60.0
                elif ntype == NodeType.PHONE:
                    ctype = CollisionType.PHONE_COLLISION
                    severity = SyntheticRiskTier.HIGH if len(c_list) >= 3 else SyntheticRiskTier.MEDIUM
                    base_score = 70.0 if len(c_list) >= 3 else 55.0
                elif ntype == NodeType.EMAIL:
                    ctype = CollisionType.EMAIL_COLLISION
                    severity = SyntheticRiskTier.HIGH if len(c_list) >= 3 else SyntheticRiskTier.MEDIUM
                    base_score = 65.0 if len(c_list) >= 3 else 50.0
                elif ntype == NodeType.ADDRESS:
                    ctype = CollisionType.ADDRESS_COLLISION
                    severity = SyntheticRiskTier.HIGH if len(c_list) >= 4 else SyntheticRiskTier.LOW
                    base_score = 60.0 if len(c_list) >= 4 else 35.0
                else:
                    ctype = CollisionType.MULTI_ATTRIBUTE_COLLISION
                    severity = SyntheticRiskTier.MEDIUM
                    base_score = 45.0

                # Scale with number of customers sharing the entity
                score = min(100.0, base_score + (len(c_list) - 2) * 10.0)

                collision = IdentityCollision(
                    collision_id=f"COLL-{entity_node.node_type.value[:3]}-{uuid.uuid4().hex[:6].upper()}",
                    collision_type=ctype,
                    shared_attribute_type=ntype,
                    shared_attribute_value=entity_node.label,
                    customer_ids=c_list,
                    severity=severity,
                    collision_score=score,
                    detected_at=datetime.now(timezone.utc),
                    details={
                        "shared_node_id": entity_id,
                        "customer_count": len(c_list),
                        "entity_label": entity_node.label
                    }
                )
                collisions.append(collision)

        return sorted(collisions, key=lambda c: c.collision_score, reverse=True)

    def find_identity_ring_clusters(self) -> List[IdentityRingCluster]:
        """
        Computes connected components across the bipartite identity network.
        Filters for components containing at least 2 customers with shared attributes.
        """
        visited: Set[str] = set()
        clusters: List[IdentityRingCluster] = []

        all_customers = [nid for nid, node in self._nodes.items() if node.node_type == NodeType.CUSTOMER]

        for cid in all_customers:
            if cid in visited:
                continue

            # BFS to find entire connected component
            component_nodes: Set[str] = set()
            queue = deque([cid])
            component_nodes.add(cid)
            visited.add(cid)

            while queue:
                curr = queue.popleft()
                for neighbor in self._adjacency.get(curr, set()):
                    if neighbor not in component_nodes:
                        component_nodes.add(neighbor)
                        visited.add(neighbor)
                        queue.append(neighbor)

            customers_in_comp = [nid for nid in component_nodes if self._nodes[nid].node_type == NodeType.CUSTOMER]
            entity_nodes_in_comp = [nid for nid in component_nodes if self._nodes[nid].node_type != NodeType.CUSTOMER]

            if len(customers_in_comp) >= 2:
                # Discovered an Identity Ring / Collision Cluster
                shared_attrs = [self._nodes[nid].label for nid in entity_nodes_in_comp]
                
                # Risk calculation for the ring
                ring_score = min(100.0, 40.0 + len(customers_in_comp) * 12.0 + len(entity_nodes_in_comp) * 5.0)
                if ring_score >= 80.0:
                    tier = SyntheticRiskTier.CRITICAL
                elif ring_score >= 60.0:
                    tier = SyntheticRiskTier.HIGH
                else:
                    tier = SyntheticRiskTier.MEDIUM

                cluster = IdentityRingCluster(
                    cluster_id=f"RING-{uuid.uuid4().hex[:6].upper()}",
                    customer_count=len(customers_in_comp),
                    customer_ids=sorted(customers_in_comp),
                    entity_nodes_count=len(entity_nodes_in_comp),
                    shared_attributes_summary=shared_attrs[:5],
                    cluster_risk_score=ring_score,
                    cluster_risk_tier=tier,
                    status=InvestigationDecision.UNDER_REVIEW
                )
                clusters.append(cluster)

        return sorted(clusters, key=lambda cl: cl.cluster_risk_score, reverse=True)
