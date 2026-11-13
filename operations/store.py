"""
FinGuard AI — Phase 21 Operations Store.
Thread-safe, tenant-scoped idempotent operational case store with SLA tracking and metric computation.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from operations.models import (
    ActivityLogEntry,
    AlertIngestRequest,
    AlertPriority,
    AnalystNote,
    CaseStatus,
    OperationalCase,
    OperationsMetricsResponse,
    SLA_MINUTES_BY_PRIORITY,
    calculate_priority_from_risk,
)


class OperationsStore:
    """Thread-safe operational case store with tenant-scoped idempotency and SLA monitoring."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cases: Dict[str, OperationalCase] = {}
        # Key: (tenant_id, idempotency_key) -> case_id
        self._idempotency_index: Dict[Tuple[str, str], str] = {}
        # Key: (tenant_id, alert_id) -> case_id
        self._alert_index: Dict[Tuple[str, str], str] = {}

    def _refresh_sla(self, case: OperationalCase) -> None:
        """Dynamically check and update SLA breach status based on current UTC time."""
        now = datetime.now(timezone.utc)
        if case.status not in (CaseStatus.RESOLVED, CaseStatus.CLOSED):
            if now > case.sla_deadline:
                case.sla_breached = True

    def ingest_alert(self, request: AlertIngestRequest) -> Tuple[OperationalCase, bool]:
        """
        Ingest alert with tenant-scoped idempotency deduplication.
        Returns (case, is_duplicate).
        """
        tenant_id = request.tenant_id or "default-tenant"

        # Determine idempotency key
        raw_key = request.idempotency_key or request.transaction_id or request.alert_id
        if not raw_key:
            raw_key = f"auto-{uuid.uuid4().hex[:12]}"
        idemp_tuple = (tenant_id, raw_key)

        with self._lock:
            # Check tenant-scoped idempotency
            if idemp_tuple in self._idempotency_index:
                existing_case_id = self._idempotency_index[idemp_tuple]
                case = self._cases[existing_case_id]
                self._refresh_sla(case)
                return case, True

            # Determine Priority
            priority = request.priority or calculate_priority_from_risk(request.risk_score)
            
            # Determine alert_id and case_id
            alert_id = request.alert_id or f"ALT-{uuid.uuid4().hex[:8].upper()}"
            case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"

            now = datetime.now(timezone.utc)
            sla_minutes = SLA_MINUTES_BY_PRIORITY.get(priority, 120)
            sla_deadline = now + timedelta(minutes=sla_minutes)

            title = request.title or f"{priority.value} Fraud Alert on {request.transaction_id or 'Transaction'}"
            description = request.description or (
                f"Automated risk detection flagged transaction with risk score {request.risk_score:.2f}."
            )

            # Initial history
            history = [
                ActivityLogEntry(
                    action="ALERT_INGESTED",
                    actor=request.source,
                    details={
                        "risk_score": request.risk_score,
                        "priority": priority.value,
                        "sla_minutes": sla_minutes,
                        "idempotency_key": raw_key,
                    },
                )
            ]

            case = OperationalCase(
                case_id=case_id,
                alert_id=alert_id,
                tenant_id=tenant_id,
                idempotency_key=raw_key,
                transaction_id=request.transaction_id,
                customer_id=request.customer_id,
                account_id=request.account_id,
                amount=request.amount,
                currency=request.currency,
                risk_score=request.risk_score,
                priority=priority,
                status=CaseStatus.OPEN,
                assigned_to=None,
                source=request.source,
                title=title,
                description=description,
                created_at=now,
                updated_at=now,
                sla_deadline=sla_deadline,
                sla_breached=False,
                notes=[],
                history=history,
                metadata=request.metadata,
            )

            self._cases[case_id] = case
            self._idempotency_index[idemp_tuple] = case_id
            self._alert_index[(tenant_id, alert_id)] = case_id
            return case, False

    def get_case(self, case_id: str) -> Optional[OperationalCase]:
        with self._lock:
            case = self._cases.get(case_id)
            if case:
                self._refresh_sla(case)
            return case

    def list_cases(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        priority: Optional[AlertPriority] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[OperationalCase]:
        with self._lock:
            results = []
            for case in self._cases.values():
                self._refresh_sla(case)
                if tenant_id and case.tenant_id != tenant_id:
                    continue
                if status and case.status != status:
                    continue
                if priority and case.priority != priority:
                    continue
                if assigned_to and case.assigned_to != assigned_to:
                    continue
                results.append(case)

            # Sort: P0 first, then nearest SLA deadline, descending created_at
            priority_rank = {AlertPriority.P0: 0, AlertPriority.P1: 1, AlertPriority.P2: 2, AlertPriority.P3: 3}
            results.sort(key=lambda c: (priority_rank.get(c.priority, 9), c.sla_deadline))
            return results[:limit]

    def assign_case(
        self, case_id: str, analyst_id: str, assigned_by: str = "supervisor"
    ) -> OperationalCase:
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found")

            now = datetime.now(timezone.utc)
            previous_analyst = case.assigned_to
            case.assigned_to = analyst_id
            case.updated_at = now

            case.history.append(
                ActivityLogEntry(
                    action="ANALYST_ASSIGNED",
                    actor=assigned_by,
                    details={
                        "previous_analyst": previous_analyst,
                        "assigned_to": analyst_id,
                    },
                )
            )
            return case

    def update_status(
        self,
        case_id: str,
        new_status: CaseStatus,
        updated_by: str = "analyst",
        reason: Optional[str] = None,
    ) -> OperationalCase:
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found")

            now = datetime.now(timezone.utc)
            old_status = case.status
            case.status = new_status
            case.updated_at = now

            case.history.append(
                ActivityLogEntry(
                    action="STATUS_UPDATED",
                    actor=updated_by,
                    details={
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "reason": reason or "",
                    },
                )
            )
            return case

    def add_note(self, case_id: str, author: str, content: str) -> OperationalCase:
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found")

            now = datetime.now(timezone.utc)
            note = AnalystNote(
                author=author,
                created_at=now,
                content=content,
            )
            case.notes.append(note)
            case.updated_at = now

            case.history.append(
                ActivityLogEntry(
                    action="NOTE_ADDED",
                    actor=author,
                    details={"note_id": note.note_id, "preview": content[:60]},
                )
            )
            return case

    def resolve_case(
        self,
        case_id: str,
        resolution: str,
        resolved_by: str = "analyst",
        notes: Optional[str] = None,
    ) -> OperationalCase:
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found")

            now = datetime.now(timezone.utc)
            case.status = CaseStatus.RESOLVED
            case.resolution = resolution
            case.resolved_by = resolved_by
            case.resolved_at = now
            case.updated_at = now

            if notes:
                case.notes.append(
                    AnalystNote(
                        author=resolved_by,
                        created_at=now,
                        content=f"[Resolution Note: {resolution}] {notes}",
                    )
                )

            case.history.append(
                ActivityLogEntry(
                    action="CASE_RESOLVED",
                    actor=resolved_by,
                    details={"resolution": resolution, "has_notes": bool(notes)},
                )
            )
            return case

    def compute_metrics(self, tenant_id: Optional[str] = None) -> OperationsMetricsResponse:
        with self._lock:
            cases = [
                c for c in self._cases.values()
                if (tenant_id is None or c.tenant_id == tenant_id)
            ]
            for c in cases:
                self._refresh_sla(c)

            total_cases = len(cases)
            open_cases = sum(1 for c in cases if c.status == CaseStatus.OPEN)
            in_review_cases = sum(1 for c in cases if c.status == CaseStatus.IN_REVIEW)
            escalated_cases = sum(1 for c in cases if c.status == CaseStatus.ESCALATED)
            resolved_cases = sum(1 for c in cases if c.status == CaseStatus.RESOLVED)
            closed_cases = sum(1 for c in cases if c.status == CaseStatus.CLOSED)

            priority_breakdown = {
                AlertPriority.P0.value: 0,
                AlertPriority.P1.value: 0,
                AlertPriority.P2.value: 0,
                AlertPriority.P3.value: 0,
            }
            for c in cases:
                priority_breakdown[c.priority.value] = priority_breakdown.get(c.priority.value, 0) + 1

            now = datetime.now(timezone.utc)
            sla_breaches = sum(1 for c in cases if c.sla_breached)
            sla_breach_rate = (sla_breaches / total_cases * 100.0) if total_cases > 0 else 0.0

            # Impending breaches (< 30 minutes left, not resolved/closed)
            sla_impending = sum(
                1 for c in cases
                if c.status not in (CaseStatus.RESOLVED, CaseStatus.CLOSED)
                and not c.sla_breached
                and (c.sla_deadline - now).total_seconds() <= 1800
            )

            # Analyst workload (active cases currently assigned)
            workload: Dict[str, int] = {}
            resolution_times = []
            for c in cases:
                if c.assigned_to and c.status not in (CaseStatus.RESOLVED, CaseStatus.CLOSED):
                    workload[c.assigned_to] = workload.get(c.assigned_to, 0) + 1
                if c.resolved_at and c.status in (CaseStatus.RESOLVED, CaseStatus.CLOSED):
                    mins = (c.resolved_at - c.created_at).total_seconds() / 60.0
                    resolution_times.append(mins)

            avg_res_time = (sum(resolution_times) / len(resolution_times)) if resolution_times else 0.0

            return OperationsMetricsResponse(
                total_alerts=total_cases,
                total_cases=total_cases,
                open_cases=open_cases,
                in_review_cases=in_review_cases,
                escalated_cases=escalated_cases,
                resolved_cases=resolved_cases,
                closed_cases=closed_cases,
                priority_breakdown=priority_breakdown,
                sla_breaches=sla_breaches,
                sla_breach_rate_pct=round(sla_breach_rate, 2),
                sla_impending_breaches=sla_impending,
                analyst_workload=workload,
                avg_resolution_time_minutes=round(avg_res_time, 2),
            )

    def clear(self) -> None:
        with self._lock:
            self._cases.clear()
            self._idempotency_index.clear()
            self._alert_index.clear()

