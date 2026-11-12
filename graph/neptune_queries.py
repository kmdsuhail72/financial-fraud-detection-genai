"""AWS Neptune Gremlin and openCypher query templates for fraud ring & relationship intelligence."""

from __future__ import annotations

from typing import Dict


class NeptuneQueryCatalog:
    """Pre-compiled Gremlin and openCypher queries compatible with Amazon Neptune."""

    @staticmethod
    def get_gremlin_queries() -> Dict[str, str]:
        return {
            "shared_device_syndicates": (
                "g.V().hasLabel('Customer').as('c1')"
                ".out('OWNS_ACCOUNT').out('USES_DEVICE').as('dev')"
                ".in('USES_DEVICE').in('OWNS_ACCOUNT').hasLabel('Customer').as('c2')"
                ".where('c1', neq('c2'))"
                ".select('c1', 'dev', 'c2')"
                ".dedup('c1', 'c2')"
            ),
            "shared_ip_clustering": (
                "g.V().hasLabel('Account').as('a1')"
                ".out('ASSOCIATED_IP').as('ip')"
                ".in('ASSOCIATED_IP').hasLabel('Account').as('a2')"
                ".where('a1', neq('a2'))"
                ".select('a1', 'ip', 'a2')"
                ".dedup('a1', 'a2')"
            ),
            "three_hop_cycle_detection": (
                "g.V().hasLabel('Account').as('a1')"
                ".out('TRANSFERRED_TO').as('a2')"
                ".out('TRANSFERRED_TO').as('a3')"
                ".out('TRANSFERRED_TO').where(eq('a1'))"
                ".path().by('id')"
            ),
            "two_hop_neighborhood": (
                "g.V('{entity_id}')"
                ".bothE().as('e').otherV().as('v1')"
                ".emit().repeat(bothE().as('e').otherV().as('v2'))"
                ".times(2)"
                ".path()"
            ),
            "high_fan_in_mules": (
                "g.V().hasLabel('Account')"
                ".where(inE('TRANSFERRED_TO').count().is(gte(5)))"
                ".project('account', 'in_count', 'out_count')"
                ".by('id')"
                ".by(inE('TRANSFERRED_TO').count())"
                ".by(outE('TRANSFERRED_TO').count())"
            ),
        }

    @staticmethod
    def get_opencypher_queries() -> Dict[str, str]:
        return {
            "shared_device_syndicates": (
                "MATCH (c1:Customer)-[:OWNS_ACCOUNT]->(a1:Account)-[:USES_DEVICE]->(d:Device)"
                "<-[:USES_DEVICE]-(a2:Account)<-[:OWNS_ACCOUNT]-(c2:Customer) "
                "WHERE c1.id < c2.id "
                "RETURN c1.id AS customer_1, c2.id AS customer_2, d.id AS device_id, d.model AS device_model"
            ),
            "shared_phone_syndicates": (
                "MATCH (c1:Customer)-[:HAS_PHONE]->(p:PhoneNumber)<-[:HAS_PHONE]-(c2:Customer) "
                "WHERE c1.id < c2.id "
                "RETURN c1.id AS customer_1, c2.id AS customer_2, p.id AS phone_number"
            ),
            "circular_fund_flow_3hop": (
                "MATCH (a:Account)-[r1:TRANSFERRED_TO]->(b:Account)-[r2:TRANSFERRED_TO]->(c:Account)-[r3:TRANSFERRED_TO]->(a) "
                "RETURN a.id AS acc_a, b.id AS acc_b, c.id AS acc_c, "
                "r1.amount AS amt1, r2.amount AS amt2, r3.amount AS amt3"
            ),
            "smurfing_mule_consolidation": (
                "MATCH (sender:Account)-[r:TRANSFERRED_TO]->(mule:Account) "
                "WITH mule, count(DISTINCT sender) AS distinct_senders, sum(r.amount) AS total_inbound "
                "WHERE distinct_senders >= 5 "
                "OPTIONAL MATCH (mule)-[r_out:TRANSFERRED_TO]->(recipient:Account) "
                "RETURN mule.id AS mule_id, distinct_senders, total_inbound, "
                "count(DISTINCT recipient) AS distinct_recipients, sum(r_out.amount) AS total_outbound"
            ),
            "k_hop_ego_network": (
                "MATCH path = (root {id: $entity_id})-[*1..2]-(neighbor) "
                "RETURN relationships(path) AS links, nodes(path) AS nodes LIMIT 100"
            ),
        }
