"""FinGuard AI — Enterprise Graph Analytics, Fraud Ring Detection & Relationship Intelligence Engine."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from graph.models import (
    CentralityMetrics,
    CyclePath,
    EdgeType,
    EntityGraphScore,
    FraudRing,
    GraphEdge,
    GraphNode,
    NodeType,
    RingRiskLevel,
    SubgraphExport,
)

logger = logging.getLogger("finguard-graph")


class FraudGraphEngine:
    """NetworkX-powered high-performance graph analytics engine for financial fraud detection."""

    def __init__(self):
        # Multigraph preserving all directed typed edges and attributes
        self.g_full = nx.MultiDiGraph()
        # Directed graph specifically for financial transfers and flow cycles
        self.g_transfers = nx.DiGraph()

    def clear(self) -> None:
        """Clears all stored nodes and edges."""
        self.g_full.clear()
        self.g_transfers.clear()

    def add_node(self, node: GraphNode) -> None:
        """Adds a typed vertex to the graph."""
        self.g_full.add_node(
            node.id,
            type=node.type.value if hasattr(node.type, "value") else str(node.type),
            label=node.label,
            risk_score=node.risk_score,
            properties=node.properties,
        )
        if node.type == NodeType.ACCOUNT:
            self.g_transfers.add_node(
                node.id,
                label=node.label,
                properties=node.properties,
            )

    def add_edge(self, edge: GraphEdge) -> None:
        """Adds a directed typed relationship between two vertices."""
        edge_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        self.g_full.add_edge(
            edge.source,
            edge.target,
            key=f"{edge_type_str}_{edge.source}_{edge.target}_{len(self.g_full.get_edge_data(edge.source, edge.target, default={}))}",
            type=edge_type_str,
            weight=edge.weight,
            properties=edge.properties,
        )

        # Mirror monetary transfers to transfer directed flow graph
        if edge.type in (EdgeType.TRANSFERRED_TO, EdgeType.PAID_MERCHANT):
            current_weight = self.g_transfers.get_edge_data(edge.source, edge.target, {}).get("weight", 0.0)
            self.g_transfers.add_edge(
                edge.source,
                edge.target,
                weight=current_weight + edge.weight,
                type=edge_type_str,
                properties=edge.properties,
            )

    def ingest_batch(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> None:
        """Atomically ingests a batch of graph entities and relationships."""
        for n in nodes:
            self.add_node(n)
        for e in edges:
            self.add_edge(e)
        logger.info("Ingested %d nodes and %d edges into GraphEngine", len(nodes), len(edges))

    def detect_fraud_rings(self) -> List[FraudRing]:
        """Detects organized fraud rings and synthetic identity syndicates sharing devices, IPs, or phones."""
        identifier_types = {NodeType.DEVICE.value, NodeType.IP_ADDRESS.value, NodeType.PHONE_NUMBER.value}
        
        # Build co-occurrence graph connecting customers/accounts sharing an identifier
        co_graph = nx.Graph()
        
        # Collect identifiers and their connected customers/accounts
        shared_map: Dict[str, Set[str]] = {}  # identifier_id -> set of entity IDs (Customer or Account)
        
        for n, data in self.g_full.nodes(data=True):
            node_type = data.get("type")
            if node_type in identifier_types:
                # Find all entities connecting to this identifier
                # In g_full, edges are (Entity) -> (Identifier) or (Identifier) -> (Entity)
                in_entities = set(self.g_full.predecessors(n))
                out_entities = set(self.g_full.successors(n))
                all_connected = in_entities.union(out_entities)
                
                # Collect distinct customers utilizing this identifier
                distinct_customers = set()
                connected_accounts = set()
                for e in all_connected:
                    etype = self.g_full.nodes.get(e, {}).get("type")
                    if etype == NodeType.CUSTOMER.value:
                        distinct_customers.add(e)
                    elif etype == NodeType.ACCOUNT.value:
                        connected_accounts.add(e)
                        for pred in self.g_full.predecessors(e):
                            if self.g_full.nodes.get(pred, {}).get("type") == NodeType.CUSTOMER.value:
                                distinct_customers.add(pred)

                # An identifier is truly shared only if 2 or more distinct customer identities use it
                if len(distinct_customers) >= 2:
                    valid_entities = set(distinct_customers).union(connected_accounts)
                    shared_map[n] = valid_entities
                    entity_list = list(valid_entities)
                    for i in range(len(entity_list)):
                        for j in range(i + 1, len(entity_list)):
                            e1, e2 = entity_list[i], entity_list[j]
                            if not co_graph.has_edge(e1, e2):
                                co_graph.add_edge(e1, e2, shared_identifiers=set())
                            co_graph[e1][e2]["shared_identifiers"].add(n)

        rings: List[FraudRing] = []
        if co_graph.number_of_nodes() == 0:
            return rings

        # Extract connected components as candidate rings
        components = list(nx.connected_components(co_graph))
        for idx, comp in enumerate(components, start=1):
            members = list(comp)
            member_customers = [m for m in members if self.g_full.nodes.get(m, {}).get("type") == NodeType.CUSTOMER.value]
            member_accounts = [m for m in members if self.g_full.nodes.get(m, {}).get("type") == NodeType.ACCOUNT.value]
            
            # If an account is in the ring, find its owning customer
            for acc in list(member_accounts):
                for pred in self.g_full.predecessors(acc):
                    if self.g_full.nodes.get(pred, {}).get("type") == NodeType.CUSTOMER.value:
                        if pred not in member_customers:
                            member_customers.append(pred)

            # Gather all shared identifiers used by any pair in this component
            all_shared_devs = set()
            all_shared_ips = set()
            all_shared_phones = set()

            sub_co = co_graph.subgraph(comp)
            for u, v, edata in sub_co.edges(data=True):
                for ident in edata.get("shared_identifiers", []):
                    ident_type = self.g_full.nodes.get(ident, {}).get("type")
                    if ident_type == NodeType.DEVICE.value:
                        all_shared_devs.add(ident)
                    elif ident_type == NodeType.IP_ADDRESS.value:
                        all_shared_ips.add(ident)
                    elif ident_type == NodeType.PHONE_NUMBER.value:
                        all_shared_phones.add(ident)

            # Compute internal transfer volume between ring members
            total_flow = 0.0
            for u in member_accounts:
                for v in member_accounts:
                    if self.g_transfers.has_edge(u, v):
                        total_flow += self.g_transfers[u][v].get("weight", 0.0)

            # Determine patterns
            patterns = []
            if len(all_shared_devs) > 0 and len(member_customers) >= 2:
                patterns.append("SYNTHETIC_IDENTITY_DEVICE_SHARING")
            if len(all_shared_phones) > 0 and len(member_customers) >= 2:
                patterns.append("MULTI_ACCOUNT_PHONE_COLLUSION")
            if len(all_shared_ips) > 0 and len(members) >= 3:
                patterns.append("BOTNET_PROXY_IP_CLUSTERING")
            if total_flow > 0:
                patterns.append("INTRA_RING_CAPITAL_CIRCULATION")

            # Calculate Ring Risk Score [0.0, 1.0]
            raw_score = (
                0.35 * (1.0 if len(all_shared_devs) > 0 else 0.0)
                + 0.25 * (1.0 if len(all_shared_phones) > 0 else 0.0)
                + 0.15 * (1.0 if len(all_shared_ips) > 0 else 0.0)
                + 0.15 * min(len(member_customers), 4) / 4.0
            )
            if total_flow > 25000:
                raw_score += 0.15
            
            risk_score = round(min(1.0, max(0.2, raw_score)), 4)
            
            if risk_score >= 0.8:
                risk_level = RingRiskLevel.CRITICAL
                recommendation = "FREEZE_LINKED_ACCOUNTS_AND_REFER_TO_FIU"
            elif risk_score >= 0.6:
                risk_level = RingRiskLevel.HIGH
                recommendation = "SUSPEND_DEVICE_ACCESS_AND_REQUEST_ENHANCED_KYC"
            elif risk_score >= 0.4:
                risk_level = RingRiskLevel.MEDIUM
                recommendation = "FLAG_FOR_EXPEDITE_ANALYST_INVESTIGATION"
            else:
                risk_level = RingRiskLevel.LOW
                recommendation = "CONTINUOUS_MONITORING"

            ring = FraudRing(
                ring_id=f"RING-{idx:03d}",
                ring_name=f"Syndicate Cluster #{idx} ({patterns[0] if patterns else 'Shared Infrastructure'})",
                risk_level=risk_level,
                risk_score=risk_score,
                member_customers=sorted(member_customers),
                member_accounts=sorted(member_accounts),
                shared_devices=sorted(list(all_shared_devs)),
                shared_ips=sorted(list(all_shared_ips)),
                shared_phones=sorted(list(all_shared_phones)),
                total_flow_amount=round(total_flow, 2),
                detected_patterns=patterns,
                recommended_action=recommendation,
            )
            rings.append(ring)

        # Sort rings descending by risk_score
        rings.sort(key=lambda r: r.risk_score, reverse=True)
        return rings

    def detect_cycles(self, max_length: int = 6) -> List[CyclePath]:
        """Detects circular fund flows (wash trading, smurfing, mule loops) in transaction network."""
        cycle_paths: List[CyclePath] = []
        if self.g_transfers.number_of_nodes() < 2:
            return cycle_paths

        try:
            raw_cycles = list(nx.simple_cycles(self.g_transfers))
        except Exception as exc:
            logger.warning("Error finding simple cycles: %s", exc)
            return cycle_paths

        idx = 1
        for cycle in raw_cycles:
            if 2 <= len(cycle) <= max_length:
                # Compute total amount flowing along the loop
                cycle_amount = 0.0
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    if self.g_transfers.has_edge(u, v):
                        cycle_amount += self.g_transfers[u][v].get("weight", 0.0)

                cycle_paths.append(
                    CyclePath(
                        cycle_id=f"CYCLE-{idx:03d}",
                        length=len(cycle),
                        nodes=cycle,
                        total_amount=round(cycle_amount, 2),
                        description=f"Circular fund transfer loop involving {len(cycle)} accounts (${cycle_amount:,.2f})",
                    )
                )
                idx += 1

        cycle_paths.sort(key=lambda c: c.total_amount, reverse=True)
        return cycle_paths

    def compute_centrality_metrics(self) -> Dict[str, CentralityMetrics]:
        """Computes PageRank, degree, and betweenness centrality over the graph."""
        res: Dict[str, CentralityMetrics] = {}
        all_nodes = list(self.g_full.nodes())
        if not all_nodes:
            return res

        # Degree centrality on full graph
        deg_cent = nx.degree_centrality(self.g_full)
        in_deg_cent = nx.in_degree_centrality(self.g_full)
        out_deg_cent = nx.out_degree_centrality(self.g_full)

        # PageRank & Betweenness on transfer graph (or full graph if transfer is tiny)
        target_graph = self.g_transfers if self.g_transfers.number_of_edges() > 0 else self.g_full
        
        try:
            pagerank = nx.pagerank(target_graph, alpha=0.85, max_iter=100)
        except Exception:
            pagerank = {n: 1.0 / max(len(all_nodes), 1) for n in all_nodes}

        try:
            betweenness = nx.betweenness_centrality(target_graph)
        except Exception:
            betweenness = {n: 0.0 for n in all_nodes}

        for n in all_nodes:
            in_deg = self.g_full.in_degree(n)
            out_deg = self.g_full.out_degree(n)
            res[n] = CentralityMetrics(
                degree_centrality=round(deg_cent.get(n, 0.0), 4),
                in_degree_centrality=round(in_deg_cent.get(n, 0.0), 4),
                out_degree_centrality=round(out_deg_cent.get(n, 0.0), 4),
                pagerank=round(pagerank.get(n, 0.0), 6),
                betweenness_centrality=round(betweenness.get(n, 0.0), 6),
                in_degree=in_deg,
                out_degree=out_deg,
            )
        return res

    def calculate_entity_risk(self, entity_id: str) -> EntityGraphScore:
        """Calculates a composite graph-based risk evaluation for a given node."""
        if not self.g_full.has_node(entity_id):
            raise KeyError(f"Entity '{entity_id}' not found in graph.")

        node_data = self.g_full.nodes[entity_id]
        raw_type = node_data.get("type", "ACCOUNT")
        try:
            entity_type = NodeType(raw_type)
        except Exception:
            entity_type = NodeType.ACCOUNT

        rings = self.detect_fraud_rings()
        cycles = self.detect_cycles()
        centrality_map = self.compute_centrality_metrics()
        centrality = centrality_map.get(entity_id, CentralityMetrics())

        risk_factors: List[str] = []
        ring_membership: Optional[str] = None
        ring_risk = 0.0

        # 1. Ring membership check
        for r in rings:
            if entity_id in r.member_customers or entity_id in r.member_accounts or entity_id in r.shared_devices or entity_id in r.shared_ips:
                ring_membership = r.ring_id
                ring_risk = r.risk_score
                risk_factors.append(f"Member of fraud ring {r.ring_id} ({r.ring_name})")
                break

        # 2. Cycle participation check
        cycle_hits = []
        cycle_penalty = 0.0
        for c in cycles:
            if entity_id in c.nodes:
                cycle_hits.append(c.cycle_id)
                cycle_penalty = max(cycle_penalty, 0.85)
                risk_factors.append(f"Participant in circular wash-trading loop {c.cycle_id} (${c.total_amount:,.2f})")

        # 3. Smurfing / Mule fan-in check
        mule_score = 0.0
        if centrality.in_degree >= 4 and centrality.out_degree <= 2:
            mule_score = 0.75
            risk_factors.append(f"High fan-in ratio ({centrality.in_degree} deposits vs {centrality.out_degree} payouts) indicating money mule consolidation")

        # 4. Shared identifier count
        shared_count = 0
        if entity_type in (NodeType.CUSTOMER, NodeType.ACCOUNT):
            # Check devices and phones
            for succ in self.g_full.successors(entity_id):
                succ_type = self.g_full.nodes.get(succ, {}).get("type")
                if succ_type in (NodeType.DEVICE.value, NodeType.PHONE_NUMBER.value, NodeType.IP_ADDRESS.value):
                    connected = set(self.g_full.predecessors(succ)).union(set(self.g_full.successors(succ)))
                    connected.discard(entity_id)
                    if len(connected) > 0:
                        shared_count += len(connected)
                        risk_factors.append(f"Shares {succ_type} '{succ}' with {len(connected)} other entities")

        shared_penalty = min(1.0, shared_count * 0.25)

        # Base threat from confirmed typologies: Fraud Ring, Wash Trading Cycle, or Smurfing Mule
        base_threat = max(ring_risk, cycle_penalty, mule_score)
        
        # Incremental multipliers from shared assets and fan-in velocity
        boost = 0.15 * shared_penalty + 0.10 * min(centrality.in_degree, 5) / 5.0
        
        if base_threat > 0:
            composite = min(1.0, base_threat * 0.85 + boost)
        else:
            composite = min(1.0, max(0.05, boost))

        final_score = round(min(1.0, max(0.05, composite)), 4)
        
        if final_score >= 0.75:
            risk_level = RingRiskLevel.CRITICAL
        elif final_score >= 0.55:
            risk_level = RingRiskLevel.HIGH
        elif final_score >= 0.30:
            risk_level = RingRiskLevel.MEDIUM
        else:
            risk_level = RingRiskLevel.LOW

        if not risk_factors:
            risk_factors.append("Standard isolated entity network pattern with no syndication indicators.")

        return EntityGraphScore(
            entity_id=entity_id,
            entity_type=entity_type,
            graph_risk_score=final_score,
            risk_level=risk_level,
            ring_membership=ring_membership,
            participating_cycles=cycle_hits,
            shared_entities_count=shared_count,
            centrality=centrality,
            risk_factors=risk_factors,
        )

    def extract_subgraph(self, center_id: str, radius: int = 2) -> SubgraphExport:
        """Extracts the k-hop ego-network around center_id for visualizer rendering."""
        if not self.g_full.has_node(center_id):
            raise KeyError(f"Entity '{center_id}' not found in graph.")

        undirected_view = self.g_full.to_undirected(as_view=True)
        sub_nodes_set = set(nx.ego_graph(undirected_view, center_id, radius=radius).nodes())

        # Extract induced subgraph from g_full
        nodes_list: List[GraphNode] = []
        for n in sub_nodes_set:
            ndata = self.g_full.nodes[n]
            raw_type = ndata.get("type", "ACCOUNT")
            try:
                ntype = NodeType(raw_type)
            except Exception:
                ntype = NodeType.ACCOUNT
            nodes_list.append(
                GraphNode(
                    id=n,
                    type=ntype,
                    label=ndata.get("label", n),
                    risk_score=ndata.get("risk_score", 0.0),
                    properties=ndata.get("properties", {}),
                )
            )

        links_list: List[GraphEdge] = []
        for u, v, k, edata in self.g_full.edges(sub_nodes_set, data=True, keys=True):
            if v in sub_nodes_set:
                raw_type = edata.get("type", "TRANSFERRED_TO")
                try:
                    etype = EdgeType(raw_type)
                except Exception:
                    etype = EdgeType.TRANSFERRED_TO
                links_list.append(
                    GraphEdge(
                        source=u,
                        target=v,
                        type=etype,
                        weight=edata.get("weight", 1.0),
                        properties=edata.get("properties", {}),
                    )
                )

        return SubgraphExport(
            center_node=center_id,
            depth_hops=radius,
            node_count=len(nodes_list),
            edge_count=len(links_list),
            nodes=nodes_list,
            links=links_list,
        )
