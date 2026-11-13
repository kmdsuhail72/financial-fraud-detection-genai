"""Parametric Gremlin Query Library for Amazon Neptune Fraud Graph Traversal (Phase 16)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


class GremlinQueryLibrary:
    """Standardized, parameterized Gremlin traversal templates for Amazon Neptune."""

    @staticmethod
    def add_vertex(label: str, vertex_id: str, properties: Optional[Dict[str, Any]] = None) -> str:
        """
        Idempotent vertex creation:
        g.V('id').fold().coalesce(unfold(), addV('label').property(id, 'id'))
        """
        escaped_id = vertex_id.replace("'", "\\'")
        escaped_label = label.replace("'", "\\'")
        query = f"g.V('{escaped_id}').fold().coalesce(unfold(), addV('{escaped_label}').property(id, '{escaped_id}'))"

        if properties:
            for k, v in properties.items():
                if isinstance(v, (int, float)):
                    query += f".property('{k}', {v})"
                elif isinstance(v, bool):
                    query += f".property('{k}', {'true' if v else 'false'})"
                else:
                    v_str = str(v).replace("'", "\\'")
                    query += f".property('{k}', '{v_str}')"
        return query

    @staticmethod
    def add_edge(
        source_id: str,
        target_id: str,
        edge_label: str,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Idempotent edge creation between existing or newly coalesced vertices.
        """
        src = source_id.replace("'", "\\'")
        tgt = target_id.replace("'", "\\'")
        lbl = edge_label.replace("'", "\\'")

        query = (
            f"g.V('{src}').as('src')"
            f".V('{tgt}').as('tgt')"
            f".coalesce(inE('{lbl}').where(outV().as('src')), addE('{lbl}').from('src').property('weight', {weight}))"
        )

        if properties:
            for k, v in properties.items():
                if isinstance(v, (int, float)):
                    query += f".property('{k}', {v})"
                elif isinstance(v, bool):
                    query += f".property('{k}', {'true' if v else 'false'})"
                else:
                    v_str = str(v).replace("'", "\\'")
                    query += f".property('{k}', '{v_str}')"
        return query

    @staticmethod
    def get_neighbors(entity_id: str, direction: str = "both") -> str:
        e_id = entity_id.replace("'", "\\'")
        if direction == "out":
            return f"g.V('{e_id}').out().dedup().project('id', 'label').by(id).by(label)"
        elif direction == "in":
            return f"g.V('{e_id}').in().dedup().project('id', 'label').by(id).by(label)"
        return f"g.V('{e_id}').both().dedup().project('id', 'label').by(id).by(label)"

    @staticmethod
    def k_hop_network(entity_id: str, depth: int = 2) -> str:
        e_id = entity_id.replace("'", "\\'")
        return (
            f"g.V('{e_id}').repeat(bothE().otherV()).times({depth}).emit().path()"
        )

    @staticmethod
    def shared_devices() -> str:
        return (
            "g.V().hasLabel('Customer').as('c1')"
            ".out('OWNS_ACCOUNT').out('USES_DEVICE').as('dev')"
            ".in('USES_DEVICE').in('OWNS_ACCOUNT').hasLabel('Customer').as('c2')"
            ".where('c1', neq('c2'))"
            ".select('c1', 'dev', 'c2')"
            ".dedup('c1', 'c2')"
        )

    @staticmethod
    def shared_ips() -> str:
        return (
            "g.V().hasLabel('Account').as('a1')"
            ".out('ASSOCIATED_IP').as('ip')"
            ".in('ASSOCIATED_IP').hasLabel('Account').as('a2')"
            ".where('a1', neq('a2'))"
            ".select('a1', 'ip', 'a2')"
            ".dedup('a1', 'a2')"
        )

    @staticmethod
    def circular_transfers(max_hops: int = 3) -> str:
        if max_hops == 3:
            return (
                "g.V().hasLabel('Account').as('a1')"
                ".out('TRANSFERRED_TO').as('a2')"
                ".out('TRANSFERRED_TO').as('a3')"
                ".out('TRANSFERRED_TO').where(eq('a1'))"
                ".path().by('id')"
            )
        return (
            f"g.V().hasLabel('Account').as('start')"
            f".repeat(out('TRANSFERRED_TO')).times({max_hops})"
            f".where(eq('start')).path().by('id')"
        )

    @staticmethod
    def high_fan_in_mules(threshold: int = 5) -> str:
        return (
            f"g.V().hasLabel('Account')"
            f".where(inE('TRANSFERRED_TO').count().is(gte({threshold})))"
            f".project('account_id', 'inbound_count', 'outbound_count')"
            f".by(id)"
            f".by(inE('TRANSFERRED_TO').count())"
            f".by(outE('TRANSFERRED_TO').count())"
        )

