"""Relationship Synchronization and Idempotency Engine for Neptune Graph (Phase 16)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from graph.models import EdgeType, NodeType
from graph.neptune_client import NeptuneGremlinClient, get_neptune_client

logger = logging.getLogger("finguard-sync")


class RelationshipSyncEngine:
    """Consumes real-time transaction events, resolves entities, and maintains Neptune graph relationships."""

    def __init__(self, client: Optional[NeptuneGremlinClient] = None):
        self.client = client or get_neptune_client()
        self._processed_hashes: Set[str] = set()
        self.metrics = {
            "events_processed": 0,
            "duplicates_skipped": 0,
            "vertices_upserted": 0,
            "edges_upserted": 0,
        }

    def compute_event_hash(self, event: Dict[str, Any]) -> str:
        """Calculates a deterministic signature for deduplication protection."""
        txn_id = str(event.get("transaction_id", event.get("event_id", "")))
        amount = str(event.get("amount", "0"))
        src = str(event.get("source_account_id", event.get("account_id", "")))
        dest = str(event.get("destination_account_id", event.get("target_account_id", "")))
        ts = str(event.get("timestamp", ""))

        raw = f"{txn_id}|{amount}|{src}|{dest}|{ts}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def sync_transaction_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Idempotently synchronizes a financial transaction into the Neptune graph.
        Creates customer, account, device, IP, and merchant vertices and semantic edges.
        """
        event_hash = self.compute_event_hash(event)
        if event_hash in self._processed_hashes:
            self.metrics["duplicates_skipped"] += 1
            return {
                "status": "DUPLICATE_SKIPPED",
                "event_hash": event_hash,
                "message": "Event previously synchronized into graph.",
            }

        txn_id = event.get("transaction_id", event.get("event_id", f"txn-{event_hash[:8]}"))
        amount = float(event.get("amount", 0.0))
        currency = str(event.get("currency", "USD"))
        timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

        customer_id = event.get("customer_id")
        source_acc = event.get("source_account_id", event.get("account_id"))
        dest_acc = event.get("destination_account_id", event.get("target_account_id"))
        device_id = event.get("device_id")
        ip_addr = event.get("ip_address")
        merchant_id = event.get("merchant_id")

        vertices_created = 0
        edges_created = 0

        # 1. Customer Vertex
        if customer_id:
            self.client.upsert_vertex(
                vertex_id=customer_id,
                label="Customer",
                node_type=NodeType.CUSTOMER,
                properties={"entity_type": "CUSTOMER", "last_active": timestamp},
            )
            vertices_created += 1

        # 2. Source Account Vertex
        if source_acc:
            self.client.upsert_vertex(
                vertex_id=source_acc,
                label="Account",
                node_type=NodeType.ACCOUNT,
                properties={"currency": currency, "last_active": timestamp},
            )
            vertices_created += 1

            # Edge: Customer OWNS_ACCOUNT Account
            if customer_id:
                self.client.upsert_edge(
                    source_id=customer_id,
                    target_id=source_acc,
                    edge_type=EdgeType.OWNS_ACCOUNT,
                    properties={"since": timestamp},
                )
                edges_created += 1

        # 3. Device Vertex & Edge
        if device_id and source_acc:
            self.client.upsert_vertex(
                vertex_id=device_id,
                label="Device",
                node_type=NodeType.DEVICE,
                properties={"device_type": event.get("device_type", "mobile")},
            )
            vertices_created += 1

            self.client.upsert_edge(
                source_id=source_acc,
                target_id=device_id,
                edge_type=EdgeType.USES_DEVICE,
                properties={"last_used": timestamp, "transaction_id": txn_id},
            )
            edges_created += 1

        # 4. IP Address Vertex & Edge
        if ip_addr and source_acc:
            self.client.upsert_vertex(
                vertex_id=ip_addr,
                label="IPAddress",
                node_type=NodeType.IP_ADDRESS,
                properties={"city": event.get("city", "Unknown")},
            )
            vertices_created += 1

            self.client.upsert_edge(
                source_id=source_acc,
                target_id=ip_addr,
                edge_type=EdgeType.ASSOCIATED_IP,
                properties={"last_seen": timestamp, "transaction_id": txn_id},
            )
            edges_created += 1

        # 5. Destination Account Vertex & Transfer Edge
        if dest_acc and source_acc:
            self.client.upsert_vertex(
                vertex_id=dest_acc,
                label="Account",
                node_type=NodeType.ACCOUNT,
                properties={"last_active": timestamp},
            )
            vertices_created += 1

            self.client.upsert_edge(
                source_id=source_acc,
                target_id=dest_acc,
                edge_type=EdgeType.TRANSFERRED_TO,
                weight=amount,
                properties={
                    "transaction_id": txn_id,
                    "amount": amount,
                    "currency": currency,
                    "timestamp": timestamp,
                },
            )
            edges_created += 1

        # 6. Merchant Vertex & Edge
        if merchant_id and source_acc:
            self.client.upsert_vertex(
                vertex_id=merchant_id,
                label="Merchant",
                node_type=NodeType.MERCHANT,
                properties={"category": event.get("merchant_category", "Retail")},
            )
            vertices_created += 1

            self.client.upsert_edge(
                source_id=source_acc,
                target_id=merchant_id,
                edge_type=EdgeType.PAID_MERCHANT,
                weight=amount,
                properties={"transaction_id": txn_id, "amount": amount},
            )
            edges_created += 1

        # Mark processed
        self._processed_hashes.add(event_hash)
        self.metrics["events_processed"] += 1
        self.metrics["vertices_upserted"] += vertices_created
        self.metrics["edges_upserted"] += edges_created

        return {
            "status": "SYNCHRONIZED",
            "event_hash": event_hash,
            "transaction_id": txn_id,
            "vertices_upserted": vertices_created,
            "edges_upserted": edges_created,
        }
