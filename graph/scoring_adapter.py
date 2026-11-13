"""Phase 7 Real-Time Fraud Scoring Integration Adapter for Neptune Graph Risk Enrichment (Phase 16)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from graph.models import (
    RingRiskLevel,
    RiskEnrichmentRequest,
    RiskEnrichmentResponse,
)
from graph.neptune_client import NeptuneGremlinClient, get_neptune_client


class GraphRiskEnricher:
    """Extracts graph intelligence features and enriches transactions prior to Phase 7 model inference."""

    def __init__(self, client: Optional[NeptuneGremlinClient] = None):
        self.client = client or get_neptune_client()

    def enrich(self, request: RiskEnrichmentRequest) -> RiskEnrichmentResponse:
        """
        Extracts relationship metrics around customer, account, device, and IP.
        Returns a standardized RiskEnrichmentResponse with graph features.
        """
        device_id = request.device_id
        ip_addr = request.ip_address
        account_id = request.account_id
        customer_id = request.customer_id

        # 1. Shared Device Analysis
        shared_device_count = 0
        if device_id:
            # Query neighbors connected to this device
            device_neighbors = self.client.get_neighbors(device_id, direction="in")
            # Distinct accounts or customers using this device
            shared_device_count = len(device_neighbors)

        # 2. Shared IP Analysis
        shared_ip_count = 0
        if ip_addr:
            ip_neighbors = self.client.get_neighbors(ip_addr, direction="in")
            shared_ip_count = len(ip_neighbors)

        # 3. Circular Transfer Flag
        circular_flag = False
        if account_id:
            cycles = self.client.find_cycles(max_length=4)
            for cycle in cycles:
                if account_id in cycle:
                    circular_flag = True
                    break

        # 4. Inbound vs Outbound Velocity
        inbound_count = 0
        outbound_count = 0
        if account_id:
            inbound_nodes = self.client.get_neighbors(account_id, direction="in")
            outbound_nodes = self.client.get_neighbors(account_id, direction="out")
            inbound_count = len(inbound_nodes)
            outbound_count = len(outbound_nodes)

        inbound_velocity_ratio = round(
            float(inbound_count) / max(1.0, float(outbound_count)), 2
        )

        # 5. Risk Factors and Composite Score Formulation
        risk_factors: List[str] = []
        base_score = 0.05

        if shared_device_count >= 3:
            risk_factors.append(f"Device {device_id} shared across {shared_device_count} entities (Device Farming)")
            base_score += 0.55
        elif shared_device_count == 2:
            risk_factors.append(f"Device {device_id} shared by 2 accounts")
            base_score += 0.20

        if shared_ip_count >= 4:
            risk_factors.append(f"IP {ip_addr} utilized by {shared_ip_count} distinct accounts")
            base_score += 0.25
        elif shared_ip_count >= 2:
            base_score += 0.10

        if circular_flag:
            risk_factors.append(f"Account {account_id} participates in circular fund flow loop")
            base_score += 0.35

        if inbound_count >= 4 and outbound_count <= 1:
            risk_factors.append(f"High fan-in mule consolidation pattern (In: {inbound_count}, Out: {outbound_count})")
            base_score += 0.20

        composite_risk = min(1.0, max(0.0, base_score))

        # Risk Classification
        if composite_risk >= 0.70:
            level = RingRiskLevel.CRITICAL
        elif composite_risk >= 0.50:
            level = RingRiskLevel.HIGH
        elif composite_risk >= 0.25:
            level = RingRiskLevel.MEDIUM
        else:
            level = RingRiskLevel.LOW

        # Machine Learning Enriched Feature Dictionary for Phase 7
        features = {
            "graph_degree_centrality": float(inbound_count + outbound_count),
            "graph_shared_device_count": float(shared_device_count),
            "graph_shared_ip_count": float(shared_ip_count),
            "graph_circular_flow_flag": 1.0 if circular_flag else 0.0,
            "graph_inbound_velocity_ratio": float(inbound_velocity_ratio),
            "graph_network_risk_score": float(round(composite_risk, 4)),
        }

        explanation = (
            f"Graph risk {composite_risk:.2f} ({level.value}): "
            + ("; ".join(risk_factors) if risk_factors else "Nominal network topology.")
        )

        return RiskEnrichmentResponse(
            transaction_id=request.transaction_id,
            graph_risk_score=round(composite_risk, 4),
            risk_level=level,
            shared_device_customers_count=shared_device_count,
            shared_ip_accounts_count=shared_ip_count,
            is_in_known_fraud_ring=shared_device_count >= 3 or circular_flag,
            circular_transfer_flag=circular_flag,
            inbound_velocity_ratio=inbound_velocity_ratio,
            network_risk_factors=risk_factors,
            enriched_features=features,
            explanation=explanation,
        )
