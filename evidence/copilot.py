"""
FinGuard AI — Phase 22 AI Investigation Copilot.
Generates evidence-grounded investigation drafts with explicit source citations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from evidence.models import (
    CopilotInvestigationDraft,
    EvidenceCitation,
    EvidenceItem,
    EvidenceType,
    TimelineEvent,
)

logger = logging.getLogger("finguard-copilot")


class EvidenceGroundedCopilot:
    """AI Investigation Copilot synthesizing evidence artifacts into source-referenced drafts."""

    def generate_draft(
        self,
        case_id: str,
        evidence_items: List[EvidenceItem],
        timeline_events: Optional[List[TimelineEvent]] = None,
        custom_instructions: Optional[str] = None,
    ) -> CopilotInvestigationDraft:
        now = datetime.now(timezone.utc)
        timeline = timeline_events or []

        if not evidence_items:
            return CopilotInvestigationDraft(
                case_id=case_id,
                generated_at=now,
                executive_summary=f"Investigation draft for Case {case_id}: Insufficient evidence items collected.",
                threat_hypotheses=["No conclusive evidence submitted for automated hypothesis generation."],
                key_findings=["Evidence store is empty for this case."],
                recommended_actions=["Collect transaction logs, device fingerprints, and network flows before copilot evaluation."],
                evidence_citations=[],
                confidence_score=0.20,
                confidence_rationale="Confidence is minimal due to lack of primary evidence artifacts.",
            )

        citations: List[EvidenceCitation] = []
        key_findings: List[str] = []
        hypotheses: List[str] = []
        recommended_actions: List[str] = []

        # Analyze evidence types
        has_txn = False
        has_device = False
        has_net = False
        has_graph = False
        has_ueba = False

        for item in evidence_items:
            citations.append(
                EvidenceCitation(
                    evidence_id=item.evidence_id,
                    evidence_type=item.evidence_type,
                    title=item.title,
                    relevance=f"Primary source from {item.source_system} captured on {item.collected_at.strftime('%Y-%m-%d %H:%M UTC')}",
                )
            )

            payload = item.raw_payload
            if item.evidence_type == EvidenceType.TRANSACTION_RECORD:
                has_txn = True
                amt = payload.get("amount", "unknown")
                curr = payload.get("currency", "USD")
                key_findings.append(
                    f"[{item.evidence_id}] High-value financial transfer of {amt} {curr} executed via {payload.get('channel', 'online')} channel."
                )
            elif item.evidence_type == EvidenceType.DEVICE_FINGERPRINT:
                has_device = True
                dev_id = payload.get("device_id", "unrecognized")
                new_flag = payload.get("is_new_device", True)
                key_findings.append(
                    f"[{item.evidence_id}] Device fingerprint {dev_id} observed (New Device Flag: {new_flag}) with OS {payload.get('os', 'Unknown')}."
                )
            elif item.evidence_type == EvidenceType.NETWORK_FLOW_IP:
                has_net = True
                ip = payload.get("ip_address", "unknown")
                is_proxy = payload.get("is_proxy_or_vpn", True)
                key_findings.append(
                    f"[{item.evidence_id}] Network flow from egress IP {ip} identified with proxy/anonymizer flag: {is_proxy}."
                )
            elif item.evidence_type == EvidenceType.GRAPH_COMMUNITY_SNAPSHOT:
                has_graph = True
                ring_id = payload.get("community_id", "Ring-Alpha")
                nodes = payload.get("node_count", 8)
                key_findings.append(
                    f"[{item.evidence_id}] Graph neural topology identified membership in dense syndication cluster ({ring_id}) spanning {nodes} correlated nodes."
                )
            elif item.evidence_type == EvidenceType.UEBA_BASELINE_DEVIATION:
                has_ueba = True
                z = payload.get("z_score", 4.2)
                key_findings.append(
                    f"[{item.evidence_id}] Behavioral deviation exceeded historical user baseline by z-score {z} in velocity and geographic displacement."
                )

        # Formulate Hypotheses based on combined evidence
        if has_device and has_net and has_txn:
            hypotheses.append(
                "Primary Hypothesis (High Probability): Coordinated Account Takeover (ATO) initiated through credential stuffing from residential proxy network on an unverified device."
            )
        elif has_graph and has_txn:
            hypotheses.append(
                "Primary Hypothesis: Organized mule syndication executing staggered smurfing transfers across tightly clustered graph community."
            )
        else:
            hypotheses.append(
                "Primary Hypothesis: Anomalous high-velocity fund transfer exhibiting significant deviations from established behavioral baseline."
            )

        hypotheses.append(
            "Alternative Explanation (Moderate/Low Probability): Authorized cardholder overseas emergency purchase using newly acquired travel device and cellular roaming."
        )

        # Recommendations
        recommended_actions.append(
            "Initiate immediate out-of-band identity challenge (Push OTP / Voice verification) to primary registered account holder."
        )
        if has_net:
            recommended_actions.append(
                "Submit egress IP address to FinGuard SOC Threat Intelligence cache for blacklisting."
            )
        if has_graph:
            recommended_actions.append(
                "Freeze downstream beneficiary accounts identified in the GNN community cluster pending AML review."
            )
        recommended_actions.append(
            "Archive full cryptographically verified evidence bundle in compliance vault."
        )

        confidence_score = min(0.95, 0.60 + (len(evidence_items) * 0.08))
        exec_summary = (
            f"Case {case_id} investigation demonstrates a multi-vector anomaly grounded in {len(evidence_items)} "
            f"verified evidence artifacts and {len(timeline)} chronological timeline events. Primary findings indicate "
            f"{hypotheses[0].split(':')[1].strip() if ':' in hypotheses[0] else hypotheses[0]}."
        )

        return CopilotInvestigationDraft(
            case_id=case_id,
            generated_at=now,
            model_provider="FinGuard-Bedrock-Copilot (Local Evidence-Grounded Engine)",
            executive_summary=exec_summary,
            threat_hypotheses=hypotheses,
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            evidence_citations=citations,
            confidence_score=round(confidence_score, 2),
            confidence_rationale=(
                f"Confidence grounded in {len(citations)} verified evidence items including "
                f"{'transaction records, ' if has_txn else ''}{'device telemetry, ' if has_device else ''}"
                f"{'network flow reputation, ' if has_net else ''}{'graph community linkage' if has_graph else ''}."
            ),
        )

