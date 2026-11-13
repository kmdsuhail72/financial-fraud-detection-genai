"""Graph Repository & Synthetic Seed Data Generator for FinGuard AI."""

from __future__ import annotations

import logging
from typing import List, Optional

from graph.fraud_graph_engine import FraudGraphEngine
from graph.models import (
    EdgeType,
    FraudRing,
    GraphEdge,
    GraphNode,
    NodeType,
    SubgraphExport,
)

logger = logging.getLogger("finguard-graph")


class GraphStore:
    """Thread-safe graph repository with pre-configured fraud rings and baseline network."""

    def __init__(self, seed: bool = True):
        self.engine = FraudGraphEngine()
        if seed:
            self.seed_demo_network()

    def seed_demo_network(self) -> None:
        """Seeds realistic fraud ring scenarios and legitimate baseline activity."""
        self.engine.clear()
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # =========================================================================
        # 1. Syndicate-Apex: Synthetic Identity & Device-Sharing Fraud Ring
        # 4 Customer personas created by a single fraudster on one compromised emulator
        # =========================================================================
        dev_apex = GraphNode(
            id="DEV-APEX-99",
            type=NodeType.DEVICE,
            label="Rooted Android Emulator (MEmu 9.0)",
            risk_score=0.92,
            properties={"os": "Android 11", "is_emulator": True, "imei": "864209048123456"},
        )
        phone_apex = GraphNode(
            id="PH-88001",
            type=NodeType.PHONE_NUMBER,
            label="+91-98765-88001 (VoIP / Virtual SIM)",
            risk_score=0.88,
            properties={"carrier": "Virtual Telecom", "line_type": "VOIP"},
        )
        ip_apex = GraphNode(
            id="IP-198.51.100.42",
            type=NodeType.IP_ADDRESS,
            label="198.51.100.42 (Mullvad VPN Exit)",
            risk_score=0.75,
            properties={"asn": "AS40065", "country": "SE", "is_vpn": True},
        )
        nodes.extend([dev_apex, phone_apex, ip_apex])

        # 4 Synthetic Customers & Accounts
        apex_customers = [
            ("CUS-801", "ACC-801", "Vikram Malhotra (Synthetic)"),
            ("CUS-802", "ACC-802", "Rahul Nambiar (Synthetic)"),
            ("CUS-803", "ACC-803", "Sameer Verma (Synthetic)"),
            ("CUS-804", "ACC-804", "Ananya Deshmukh (Synthetic)"),
        ]

        for cus_id, acc_id, name in apex_customers:
            c_node = GraphNode(
                id=cus_id,
                type=NodeType.CUSTOMER,
                label=name,
                risk_score=0.85,
                properties={"kyc_tier": "TIER_1", "synthetic_suspicion": True},
            )
            a_node = GraphNode(
                id=acc_id,
                type=NodeType.ACCOUNT,
                label=f"Current Account {acc_id}",
                risk_score=0.82,
                properties={"balance": 34000.0, "currency": "INR", "status": "ACTIVE"},
            )
            nodes.extend([c_node, a_node])

            # Relationships: Customer owns Account, uses Device, has Phone, associates with IP
            edges.append(GraphEdge(source=cus_id, target=acc_id, type=EdgeType.OWNS_ACCOUNT, weight=1.0))
            edges.append(GraphEdge(source=acc_id, target=dev_apex.id, type=EdgeType.USES_DEVICE, weight=1.0))
            edges.append(GraphEdge(source=cus_id, target=phone_apex.id, type=EdgeType.HAS_PHONE, weight=1.0))
            edges.append(GraphEdge(source=acc_id, target=ip_apex.id, type=EdgeType.ASSOCIATED_IP, weight=1.0))

        # Intra-ring transfers between synthetic accounts
        edges.append(GraphEdge(source="ACC-801", target="ACC-802", type=EdgeType.TRANSFERRED_TO, weight=25000.0))
        edges.append(GraphEdge(source="ACC-802", target="ACC-803", type=EdgeType.TRANSFERRED_TO, weight=24500.0))
        edges.append(GraphEdge(source="ACC-803", target="ACC-804", type=EdgeType.TRANSFERRED_TO, weight=24000.0))

        # =========================================================================
        # 2. Mule-Loop-Bravo: Circular Wash Trading / Smurfing Loop
        # 3 Accounts moving funds in a closed loop (ACC-701 -> ACC-702 -> ACC-703 -> ACC-701)
        # =========================================================================
        for i in (1, 2, 3):
            cid = f"CUS-70{i}"
            aid = f"ACC-70{i}"
            c_node = GraphNode(
                id=cid,
                type=NodeType.CUSTOMER,
                label=f"Mule Operator #{i}",
                risk_score=0.79,
                properties={"risk_rating": "HIGH", "flags": ["MULE_SUSPECT"]},
            )
            a_node = GraphNode(
                id=aid,
                type=NodeType.ACCOUNT,
                label=f"Loop Mule Account {aid}",
                risk_score=0.84,
                properties={"balance": 65000.0, "currency": "INR"},
            )
            nodes.extend([c_node, a_node])
            edges.append(GraphEdge(source=cid, target=aid, type=EdgeType.OWNS_ACCOUNT, weight=1.0))

        # Circular transfers forming cycle of length 3
        edges.append(GraphEdge(source="ACC-701", target="ACC-702", type=EdgeType.TRANSFERRED_TO, weight=65000.0, properties={"channel": "IMPS"}))
        edges.append(GraphEdge(source="ACC-702", target="ACC-703", type=EdgeType.TRANSFERRED_TO, weight=64800.0, properties={"channel": "IMPS"}))
        edges.append(GraphEdge(source="ACC-703", target="ACC-701", type=EdgeType.TRANSFERRED_TO, weight=64500.0, properties={"channel": "IMPS"}))

        # =========================================================================
        # 3. Smurf-Node-Gamma: Fan-In Smurfing Node to Offshore Terminal
        # 5 Micro-senders -> 1 Mule Consolidation Account -> Offshore Merchant
        # =========================================================================
        mule_acc = GraphNode(
            id="ACC-600",
            type=NodeType.ACCOUNT,
            label="Consolidation Mule Account ACC-600",
            risk_score=0.89,
            properties={"balance": 1200.0, "velocity_alert": True},
        )
        offshore_merch = GraphNode(
            id="MERCH-OFFSHORE-99",
            type=NodeType.MERCHANT,
            label="CryptoGateway International Ltd",
            risk_score=0.85,
            properties={"mcc": "6051", "jurisdiction": "Seychelles"},
        )
        nodes.extend([mule_acc, offshore_merch])

        for s_idx in range(1, 6):
            s_acc_id = f"ACC-60{s_idx}"
            s_node = GraphNode(
                id=s_acc_id,
                type=NodeType.ACCOUNT,
                label=f"Smurf Payer {s_acc_id}",
                risk_score=0.45,
                properties={"balance": 5000.0},
            )
            nodes.append(s_node)
            # Transfer into consolidation mule
            edges.append(GraphEdge(source=s_acc_id, target="ACC-600", type=EdgeType.TRANSFERRED_TO, weight=4900.0))

        # Mule payouts in bulk to offshore gateway
        edges.append(GraphEdge(source="ACC-600", target="MERCH-OFFSHORE-99", type=EdgeType.PAID_MERCHANT, weight=24500.0))

        # =========================================================================
        # 4. Legitimate Baseline Entities
        # Clean accounts and transactions for standard reference
        # =========================================================================
        legit_cus = GraphNode(
            id="CUS-100045",
            type=NodeType.CUSTOMER,
            label="Sunita Patel (Verified Resident)",
            risk_score=0.08,
            properties={"kyc_tier": "TIER_3_FULL", "tenure_years": 7},
        )
        legit_acc = GraphNode(
            id="ACC-100045",
            type=NodeType.ACCOUNT,
            label="Savings Account ACC-100045",
            risk_score=0.06,
            properties={"balance": 182000.0, "currency": "INR"},
        )
        legit_dev = GraphNode(
            id="DEV-IPHONE-15",
            type=NodeType.DEVICE,
            label="Apple iPhone 15 Pro",
            risk_score=0.05,
            properties={"os": "iOS 17.4", "is_emulator": False},
        )
        legit_phone = GraphNode(
            id="PH-98200",
            type=NodeType.PHONE_NUMBER,
            label="+91-98200-11223 (Postpaid)",
            risk_score=0.04,
            properties={"carrier": "Airtel India", "line_type": "POSTPAID"},
        )
        amazon_merch = GraphNode(
            id="MERCH-AMAZON-01",
            type=NodeType.MERCHANT,
            label="Amazon India Retail",
            risk_score=0.02,
            properties={"mcc": "5311", "category": "E-Commerce"},
        )
        nodes.extend([legit_cus, legit_acc, legit_dev, legit_phone, amazon_merch])

        edges.append(GraphEdge(source="CUS-100045", target="ACC-100045", type=EdgeType.OWNS_ACCOUNT, weight=1.0))
        edges.append(GraphEdge(source="ACC-100045", target="DEV-IPHONE-15", type=EdgeType.USES_DEVICE, weight=1.0))
        edges.append(GraphEdge(source="CUS-100045", target="PH-98200", type=EdgeType.HAS_PHONE, weight=1.0))
        edges.append(GraphEdge(source="ACC-100045", target="MERCH-AMAZON-01", type=EdgeType.PAID_MERCHANT, weight=3499.0))

        self.engine.ingest_batch(nodes, edges)
        logger.info("Successfully seeded demo graph network: %d nodes, %d edges", len(nodes), len(edges))


# Global singleton instance
graph_store = GraphStore(seed=True)

