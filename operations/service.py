"""
FinGuard AI — Phase 21 Operations Service.
Singleton service coordinator for alert ingestion, case lifecycle, SLA management, and operations metrics.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from operations.models import (
    AlertIngestRequest,
    AlertIngestResponse,
    AlertPriority,
    AnalystNoteRequest,
    CaseAssignRequest,
    CaseResolveRequest,
    CaseStatus,
    CaseStatusUpdateRequest,
    OperationalCase,
    OperationsMetricsResponse,
)
from operations.store import OperationsStore

logger = logging.getLogger("finguard-operations")


class OperationsService:
    """Service layer coordinating operational case workflows and SLA enforcement."""

    def __init__(self, store: Optional[OperationsStore] = None) -> None:
        self.store = store or OperationsStore()

    def ingest_alert(self, request: AlertIngestRequest) -> AlertIngestResponse:
        case, is_duplicate = self.store.ingest_alert(request)
        msg = "Alert already processed (idempotent duplicate)" if is_duplicate else "Alert ingested and case created"
        logger.info(
            f"Ingested alert {case.alert_id} for tenant {case.tenant_id} -> case {case.case_id} (duplicate={is_duplicate})"
        )
        return AlertIngestResponse(
            alert_id=case.alert_id,
            case_id=case.case_id,
            tenant_id=case.tenant_id,
            idempotency_key=case.idempotency_key,
            priority=case.priority,
            status=case.status,
            risk_score=case.risk_score,
            created_at=case.created_at,
            sla_deadline=case.sla_deadline,
            is_duplicate=is_duplicate,
            message=msg,
        )

    def get_case(self, case_id: str) -> Optional[OperationalCase]:
        return self.store.get_case(case_id)

    def list_cases(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        priority: Optional[AlertPriority] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[OperationalCase]:
        return self.store.list_cases(
            tenant_id=tenant_id,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            limit=limit,
        )

    def assign_case(self, case_id: str, request: CaseAssignRequest) -> OperationalCase:
        return self.store.assign_case(
            case_id=case_id,
            analyst_id=request.analyst_id,
            assigned_by=request.assigned_by or "supervisor",
        )

    def update_case_status(self, case_id: str, request: CaseStatusUpdateRequest) -> OperationalCase:
        return self.store.update_status(
            case_id=case_id,
            new_status=request.status,
            updated_by=request.updated_by,
            reason=request.reason,
        )

    def add_note(self, case_id: str, request: AnalystNoteRequest) -> OperationalCase:
        content = request.get_content()
        return self.store.add_note(
            case_id=case_id,
            author=request.author,
            content=content,
        )

    def resolve_case(self, case_id: str, request: CaseResolveRequest) -> OperationalCase:
        return self.store.resolve_case(
            case_id=case_id,
            resolution=request.resolution,
            resolved_by=request.resolved_by,
            notes=request.notes,
        )

    def get_metrics(self, tenant_id: Optional[str] = None) -> OperationsMetricsResponse:
        return self.store.compute_metrics(tenant_id=tenant_id)

    def seed_demo_data(self) -> None:
        """Populate initial representative operational alerts across all priority tiers."""
        demo_alerts = [
            AlertIngestRequest(
                alert_id="ALT-DEMO-001",
                tenant_id="tenant-acme-bank",
                transaction_id="TXN-90812-BURST",
                customer_id="CUST-4412",
                amount=8500.0,
                currency="USD",
                risk_score=0.96,
                priority=AlertPriority.P0,
                source="TEMPORAL_GRU_STREAM",
                title="P0: Rapid Micro-Burst Velocity & Ring Linkage",
                description="Cluster of 14 high-velocity transactions flagged by Temporal GRU and GNN ring detection.",
            ),
            AlertIngestRequest(
                alert_id="ALT-DEMO-002",
                tenant_id="tenant-acme-bank",
                transaction_id="TXN-77210-UEBA",
                customer_id="CUST-1190",
                amount=3200.0,
                currency="USD",
                risk_score=0.78,
                priority=AlertPriority.P1,
                source="UEBA_ANOMALY_ENGINE",
                title="P1: Impossible Travel & Off-Hours Device Anomaly",
                description="Login location jump from London to Singapore within 22 minutes with new device fingerprint.",
            ),
            AlertIngestRequest(
                alert_id="ALT-DEMO-003",
                tenant_id="tenant-acme-bank",
                transaction_id="TXN-55319-THREAT",
                customer_id="CUST-8831",
                amount=1450.0,
                currency="USD",
                risk_score=0.52,
                priority=AlertPriority.P2,
                source="THREAT_INTEL_IOC",
                title="P2: Tor Exit Node / Residential Proxy Transaction",
                description="Transaction originated from IP known for credential stuffing and residential proxy routing.",
            ),
            AlertIngestRequest(
                alert_id="ALT-DEMO-004",
                tenant_id="tenant-acme-bank",
                transaction_id="TXN-10022-ROUTINE",
                customer_id="CUST-2234",
                amount=120.0,
                currency="USD",
                risk_score=0.18,
                priority=AlertPriority.P3,
                source="DECISION_ENGINE",
                title="P3: Routine International Cardholder Purchase",
                description="Slightly anomalous merchant category code with valid 3D Secure verification.",
            ),
        ]
        for alert in demo_alerts:
            self.ingest_alert(alert)


# Global singleton instance
_GLOBAL_OPERATIONS_SERVICE: Optional[OperationsService] = None


def get_operations_service() -> OperationsService:
    global _GLOBAL_OPERATIONS_SERVICE
    if _GLOBAL_OPERATIONS_SERVICE is None:
        _GLOBAL_OPERATIONS_SERVICE = OperationsService()
        _GLOBAL_OPERATIONS_SERVICE.seed_demo_data()
    return _GLOBAL_OPERATIONS_SERVICE

