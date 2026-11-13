"""Phase 17 — Advanced Fraud Intelligence, Graph Algorithms & Predictive Network Analytics."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from graph.graph_store import GraphStore, graph_store
from graph.models import (
    CommunityCluster,
    NodeType,
    PathAnalysisRequest,
    PathAnalysisResponse,
    PredictiveNetworkRisk,
    RingRiskLevel,
)
from graph.neptune_client import NeptuneGremlinClient, get_neptune_client

logger = logging.getLogger("finguard-advanced-analytics")


class AdvancedNetworkAnalytics:
    """Enterprise graph algorithm suite for community detection, centrality, PageRank, and predictive risk."""

    def __init__(
        self,
        store: Optional[GraphStore] = None,
        neptune: Optional[NeptuneGremlinClient] = None,
    ):
        self.store = store or graph_store
        self.neptune = neptune or get_neptune_client()

    def get_undirected_graph(self) -> nx.Graph:
        """Returns simple undirected view of current graph for community algorithms."""
        return nx.Graph(self.store.engine.g_full)

    def get_directed_graph(self) -> nx.DiGraph:
        """Returns directed view of current graph for centrality & PageRank."""
        return self.store.engine.g_full

    # =========================================================================
    # 1. Community Detection (Louvain with Connected Components Fallback)
    # =========================================================================
    def detect_communities(self) -> List[CommunityCluster]:
        """
        Executes Louvain community detection across the financial network.
        Falls back to connected components if network is small or disconnected.
        """
        g_undir = self.get_undirected_graph()
        if g_undir.number_of_nodes() == 0:
            return []

        communities_raw: List[Set[str]] = []
        try:
            communities_raw = list(nx.community.louvain_communities(g_undir, seed=42))
        except Exception as exc:
            logger.warning("Louvain failed, falling back to connected components: %s", exc)
            communities_raw = [set(c) for c in nx.connected_components(g_undir)]

        results: List[CommunityCluster] = []
        cycles = self.store.engine.detect_cycles(max_length=4)
        cycle_nodes: Set[str] = set()
        for cyc in cycles:
            cycle_nodes.update(cyc.nodes)

        shared_devices = self.neptune.find_shared_devices()
        shared_dev_ids = {sd["device_id"] for sd in shared_devices}

        shared_ips = self.neptune.find_shared_ips()
        shared_ip_ids = {sip["ip_address"] for sip in shared_ips}

        for idx, comm in enumerate(communities_raw, start=1):
            members = sorted(list(comm))
            size = len(members)
            sub = g_undir.subgraph(members)
            density = round(float(nx.density(sub)), 3)

            has_dev = any(m in shared_dev_ids for m in members)
            has_ip = any(m in shared_ip_ids for m in members)
            has_cycle = any(m in cycle_nodes for m in members)

            indicators: List[str] = []
            risk_score = 0.05

            if has_dev:
                indicators.append("Shared physical device infrastructure in community")
                risk_score += 0.40
            if has_ip:
                indicators.append("Shared network IP ingress hub in community")
                risk_score += 0.25
            if has_cycle:
                indicators.append("Circular fund transfer loop identified in community")
                risk_score += 0.35
            if density >= 0.35 and size >= 4:
                indicators.append(f"Abnormally high internal interconnectivity (density: {density})")
                risk_score += 0.20

            final_risk = min(1.0, round(risk_score, 3))
            if final_risk >= 0.75:
                lvl = RingRiskLevel.CRITICAL
            elif final_risk >= 0.50:
                lvl = RingRiskLevel.HIGH
            elif final_risk >= 0.25:
                lvl = RingRiskLevel.MEDIUM
            else:
                lvl = RingRiskLevel.LOW

            cluster = CommunityCluster(
                community_id=f"COMM-{idx:02d}",
                members=members,
                size=size,
                density=density,
                risk_score=final_risk,
                risk_level=lvl,
                has_shared_device=has_dev,
                has_shared_ip=has_ip,
                has_circular_loop=has_cycle,
                suspicious_indicators=indicators,
            )
            results.append(cluster)

        # Sort descending by risk score
        results.sort(key=lambda c: (c.risk_score, c.size), reverse=True)
        return results

    # =========================================================================
    # 2. Graph Centrality and PageRank
    # =========================================================================
    def calculate_pagerank(self, alpha: float = 0.85) -> Dict[str, float]:
        """Calculates PageRank authority flow across the network."""
        g = self.get_directed_graph()
        if g.number_of_nodes() == 0:
            return {}
        try:
            pr = nx.pagerank(g, alpha=alpha, weight="weight")
            return {k: round(float(v), 5) for k, v in pr.items()}
        except Exception:
            # Fallback uniform
            n = g.number_of_nodes()
            return {k: round(1.0 / n, 5) for k in g.nodes()}

    def calculate_centrality(self, entity_id: str) -> Dict[str, float]:
        """Calculates point-in-time centrality measurements for an entity."""
        g = self.get_directed_graph()
        if entity_id not in g:
            return {
                "degree_centrality": 0.0,
                "in_degree_centrality": 0.0,
                "out_degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
                "clustering_coefficient": 0.0,
            }

        deg_c = nx.degree_centrality(g).get(entity_id, 0.0)
        in_c = nx.in_degree_centrality(g).get(entity_id, 0.0)
        out_c = nx.out_degree_centrality(g).get(entity_id, 0.0)

        # Betweenness computed on sample / subgraph for high efficiency
        betweenness = nx.betweenness_centrality(g, weight="weight").get(entity_id, 0.0)

        # Clustering coefficient on simple undirected projection
        g_simple = nx.Graph(g)
        clustering = nx.clustering(g_simple, entity_id)

        return {
            "degree_centrality": round(float(deg_c), 4),
            "in_degree_centrality": round(float(in_c), 4),
            "out_degree_centrality": round(float(out_c), 4),
            "betweenness_centrality": round(float(betweenness), 4),
            "clustering_coefficient": round(float(clustering), 4),
        }

    # =========================================================================
    # 3. Transaction Path Analysis (Shortest Paths)
    # =========================================================================
    def find_shortest_path(self, request: PathAnalysisRequest) -> PathAnalysisResponse:
        """Finds shortest relationship trail between source and target entities."""
        g = self.get_directed_graph()
        src = request.source_id
        dst = request.target_id

        # Check in directed graph first, then undirected view
        path_nodes: List[str] = []
        path_rels: List[str] = []

        if src in g and dst in g:
            try:
                path_nodes = nx.shortest_path(g, source=src, target=dst)
            except nx.NetworkXNoPath:
                try:
                    # Fallback to undirected path (any connection)
                    g_u = g.to_undirected()
                    path_nodes = nx.shortest_path(g_u, source=src, target=dst)
                except nx.NetworkXNoPath:
                    path_nodes = []

        if not path_nodes:
            return PathAnalysisResponse(
                source_id=src,
                target_id=dst,
                path_exists=False,
                shortest_path_hops=0,
                path_nodes=[],
                path_relationships=[],
                risk_summary=f"No relationship path connects '{src}' and '{dst}'.",
            )

        # Collect edge types along path
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if g.has_edge(u, v):
                edge_data = g.get_edge_data(u, v, default={})
                path_rels.append(edge_data.get("type", "CONNECTED_TO"))
            elif g.has_edge(v, u):
                edge_data = g.get_edge_data(v, u, default={})
                path_rels.append(f"INVERSE_{edge_data.get('type', 'CONNECTED_TO')}")
            else:
                path_rels.append("RELATIONSHIP")

        hops = len(path_nodes) - 1
        risk_summary = (
            f"Path found spanning {hops} hops: "
            + " -> ".join([f"{path_nodes[i]} ({path_rels[i]})" for i in range(len(path_rels))])
            + f" -> {path_nodes[-1]}."
        )

        return PathAnalysisResponse(
            source_id=src,
            target_id=dst,
            path_exists=True,
            shortest_path_hops=hops,
            path_nodes=path_nodes,
            path_relationships=path_rels,
            risk_summary=risk_summary,
        )

    # =========================================================================
    # 4. Predictive Fraud-Ring Risk Scoring
    # =========================================================================
    def predict_entity_risk(self, entity_id: str) -> PredictiveNetworkRisk:
        """
        Calculates advisory predictive fraud risk based on network prominence,
        community membership, and topological red flags.
        """
        g = self.get_directed_graph()
        if entity_id not in g:
            return PredictiveNetworkRisk(
                entity_id=entity_id,
                predictive_fraud_risk=0.05,
                advisory_risk_level=RingRiskLevel.LOW,
                risk_factors=["Entity has no recorded relationships in graph database."],
                recommendation="Maintain standard monitoring.",
            )

        centrality = self.calculate_centrality(entity_id)
        pr_map = self.calculate_pagerank()
        pr_score = pr_map.get(entity_id, 0.0)

        # Community lookup
        communities = self.detect_communities()
        matched_comm = None
        for comm in communities:
            if entity_id in comm.members:
                matched_comm = comm
                break

        comm_risk = matched_comm.risk_score if matched_comm else 0.05
        betweenness = centrality["betweenness_centrality"]

        factors: List[str] = []
        if matched_comm and matched_comm.risk_level in (RingRiskLevel.CRITICAL, RingRiskLevel.HIGH):
            factors.append(f"Member of high-risk community {matched_comm.community_id} (Score: {matched_comm.risk_score:.2f})")
            factors.extend(matched_comm.suspicious_indicators)

        if betweenness >= 0.10:
            factors.append(f"High betweenness centrality ({betweenness:.3f}): Intermediary fund routing hub")

        if pr_score >= 0.08:
            factors.append(f"High PageRank prominence ({pr_score:.3f}): Key authority vertex in payment network")

        # Risk Formulation
        base_pred = 0.45 * comm_risk + 0.25 * min(1.0, betweenness * 8.0) + 0.15 * min(1.0, pr_score * 12.0)
        final_risk = min(1.0, max(0.05, round(base_pred, 3)))

        if final_risk >= 0.70:
            lvl = RingRiskLevel.CRITICAL
            rec = "Advisory Freeze: Flag entity accounts for human investigator expedite review."
        elif final_risk >= 0.45:
            lvl = RingRiskLevel.HIGH
            rec = "Step-Up Verification: Enforce secondary device authentication on subsequent transfers."
        elif final_risk >= 0.25:
            lvl = RingRiskLevel.MEDIUM
            rec = "Watchlist Monitor: Observe transaction routing across neighboring accounts."
        else:
            lvl = RingRiskLevel.LOW
            rec = "Standard Automated Clearance: Activity topology conforms to normal patterns."

        return PredictiveNetworkRisk(
            entity_id=entity_id,
            pagerank=round(pr_score, 4),
            betweenness_centrality=betweenness,
            degree_centrality=centrality["degree_centrality"],
            clustering_coefficient=centrality["clustering_coefficient"],
            community_id=matched_comm.community_id if matched_comm else None,
            community_risk_score=comm_risk,
            predictive_fraud_risk=final_risk,
            advisory_risk_level=lvl,
            risk_factors=factors or ["Nominal graph connectivity."],
            recommendation=rec,
        )


# Global singleton instance
_advanced_analytics_instance: Optional[AdvancedNetworkAnalytics] = None


def get_advanced_analytics() -> AdvancedNetworkAnalytics:
    global _advanced_analytics_instance
    if _advanced_analytics_instance is None:
        _advanced_analytics_instance = AdvancedNetworkAnalytics()
    return _advanced_analytics_instance
