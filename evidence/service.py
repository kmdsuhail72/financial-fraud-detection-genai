"""
FinGuard AI — Phase 22 Evidence Service.
Singleton service coordinator for evidence collection, SHA-256 verification, copilot drafts, and reports.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from evidence.models import (
    AnalystInvestigationReport,
    CaseTimeline,
    CopilotInvestigationDraft,
    EvidenceAuditEntry,
    EvidenceCollectRequest,
    EvidenceItem,
    EvidenceType,
    IntegrityVerificationResult,
    ReportGenerateRequest,
    TimelineEvent,
)
from evidence.store import EvidenceStore

logger = logging.getLogger("finguard-evidence-service")


class EvidenceService:
    """Service layer managing digital evidence lifecycle and AI copilot integration."""

    def __init__(self, store: Optional[EvidenceStore] = None) -> None:
        self.store = store or EvidenceStore()

    def collect_evidence(
        self, request: EvidenceCollectRequest, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> EvidenceItem:
        return self.store.collect_evidence(request, actor=actor, ip_address=ip_address)

    def get_evidence(
        self, evidence_id: str, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> Optional[EvidenceItem]:
        return self.store.get_evidence(evidence_id, actor=actor, ip_address=ip_address)

    def list_case_evidence(
        self, case_id: str, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> List[EvidenceItem]:
        return self.store.list_case_evidence(case_id, actor=actor, ip_address=ip_address)

    def verify_integrity(
        self, evidence_id: str, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> IntegrityVerificationResult:
        return self.store.verify_integrity(evidence_id, actor=actor, ip_address=ip_address)

    def verify_all_case_evidence(
        self, case_id: str, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> List[IntegrityVerificationResult]:
        return self.store.verify_all_case_evidence(case_id, actor=actor, ip_address=ip_address)

    def add_timeline_event(
        self, event: TimelineEvent, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> TimelineEvent:
        return self.store.add_timeline_event(event, actor=actor, ip_address=ip_address)

    def get_case_timeline(
        self, case_id: str, actor: str = "analyst", ip_address: Optional[str] = None
    ) -> CaseTimeline:
        return self.store.get_case_timeline(case_id, actor=actor, ip_address=ip_address)

    def generate_copilot_draft(
        self,
        case_id: str,
        actor: str = "analyst",
        custom_instructions: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> CopilotInvestigationDraft:
        return self.store.generate_copilot_draft(
            case_id, actor=actor, custom_instructions=custom_instructions, ip_address=ip_address
        )

    def generate_report(
        self,
        case_id: str,
        request: ReportGenerateRequest,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> AnalystInvestigationReport:
        return self.store.generate_report(case_id, request, actor=actor, ip_address=ip_address)

    def get_report(self, report_id: str, actor: str = "analyst") -> Optional[AnalystInvestigationReport]:
        return self.store.get_report(report_id, actor=actor)

    def list_reports(self, case_id: Optional[str] = None) -> List[AnalystInvestigationReport]:
        return self.store.list_reports(case_id=case_id)

    def get_audit_log(
        self,
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvidenceAuditEntry]:
        return self.store.get_audit_log(case_id=case_id, evidence_id=evidence_id, limit=limit)

    def seed_demo_evidence(self) -> None:
        """Seed representative forensic evidence bundle for demonstration case CASE-P0-9901."""
        case_id = "CASE-P0-9901"
        self.collect_evidence(
            EvidenceCollectRequest(
                case_id=case_id,
                evidence_type=EvidenceType.TRANSACTION_RECORD,
                title="Rapid Micro-Burst Primary Transaction",
                description="High velocity wire transaction flagged by real-time decision engine.",
                source_system="CORE_BANKING_LEDGER",
                payload={
                    "transaction_id": "TXN-90812-BURST",
                    "customer_id": "CUST-4412",
                    "amount": 8500.0,
                    "currency": "USD",
                    "channel": "API_INSTANT_TRANSFER",
                    "merchant": "CRYPTO_EXCHANGE_RAMP",
                },
                collector="finguard.ingest",
            )
        )

        self.collect_evidence(
            EvidenceCollectRequest(
                case_id=case_id,
                evidence_type=EvidenceType.DEVICE_FINGERPRINT,
                title="Unrecognized High-Risk Android Device Telemetry",
                description="New device fingerprint recorded 4 minutes prior to fund transfer attempt.",
                source_system="MOBILE_SDK_TELEMETRY",
                payload={
                    "device_id": "DEV-ANON-8812X",
                    "is_new_device": True,
                    "os": "Android 14 (Rooted/Magisk Detected)",
                    "browser": "HeadlessChrome/124.0",
                    "screen_resolution": "1080x2400",
                },
                collector="finguard.telemetry",
            )
        )

        self.collect_evidence(
            EvidenceCollectRequest(
                case_id=case_id,
                evidence_type=EvidenceType.NETWORK_FLOW_IP,
                title="Residential Proxy Egress Network Flow",
                description="Network packet telemetry mapped to known commercial rotating proxy.",
                source_system="AWS_VPC_FLOW_LOGS",
                payload={
                    "ip_address": "198.51.100.44",
                    "asn": "AS40021-HOSTING",
                    "is_proxy_or_vpn": True,
                    "threat_reputation_score": 0.89,
                },
                collector="finguard.soc",
            )
        )

        self.collect_evidence(
            EvidenceCollectRequest(
                case_id=case_id,
                evidence_type=EvidenceType.GRAPH_COMMUNITY_SNAPSHOT,
                title="GNN Smurfing Fraud Ring Topology Snapshot",
                description="Community detection Louvain cluster associating customer with 8 mule nodes.",
                source_system="NEPTUNE_GRAPH_ENGINE",
                payload={
                    "community_id": "RING-MULE-CLUSTER-09",
                    "node_count": 8,
                    "edge_count": 22,
                    "graph_fraud_probability": 0.94,
                },
                collector="finguard.graph",
            )
        )


# Global singleton instance
_GLOBAL_EVIDENCE_SERVICE: Optional[EvidenceService] = None


def get_evidence_service() -> EvidenceService:
    global _GLOBAL_EVIDENCE_SERVICE
    if _GLOBAL_EVIDENCE_SERVICE is None:
        _GLOBAL_EVIDENCE_SERVICE = EvidenceService()
        _GLOBAL_EVIDENCE_SERVICE.seed_demo_evidence()
    return _GLOBAL_EVIDENCE_SERVICE

