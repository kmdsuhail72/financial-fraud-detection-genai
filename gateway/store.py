"""
FinGuard AI — Phase 32: In-Memory Multi-Tenant Store & Gateway Telemetry.
Isolates resources strictly per tenant and aggregates gateway traffic metrics.
"""
from __future__ import annotations

from collections import defaultdict
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from gateway.models import GatewayMetrics, TenantCase


class GatewayStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._cases: Dict[str, TenantCase] = {}
        self._tenant_traffic: Dict[str, int] = defaultdict(int)
        self._metrics_counts = {
            "total_requests": 0,
            "authenticated_requests": 0,
            "service_requests": 0,
            "rate_limited_requests": 0,
            "latencies": [],
        }
        self._seed_default_data()

    def _seed_default_data(self):
        """Seeds multi-tenant demo cases."""
        now = datetime.now(timezone.utc)

        # Tenant Alpha cases
        c1 = TenantCase(
            case_id="CASE-ALPHA-01",
            tenant_id="tenant-alpha",
            title="High-velocity structuring anomaly detected",
            description="Rapid structured UPI transfers just below reporting limits",
            severity="HIGH",
            status="INVESTIGATION",
            amount=320000.0,
            created_at=now,
        )
        c2 = TenantCase(
            case_id="CASE-ALPHA-02",
            tenant_id="tenant-alpha",
            title="Cross-border payment city mismatch",
            description="Origin and destination IP distance exceeds possible travel velocity",
            severity="MEDIUM",
            status="OPEN",
            amount=180000.0,
            created_at=now,
        )

        # Tenant Beta case
        c3 = TenantCase(
            case_id="CASE-BETA-01",
            tenant_id="tenant-beta",
            title="Synthetic identity collision ring detected",
            description="Matching document ID and contact coordinates across 4 applicant records",
            severity="CRITICAL",
            status="ESCALATED",
            amount=550000.0,
            created_at=now,
        )

        for c in [c1, c2, c3]:
            self._cases[c.case_id] = c

    def list_tenant_cases(self, tenant_id: str) -> List[TenantCase]:
        """Strictly partitions and returns only cases owned by the authenticated tenant."""
        with self._lock:
            cases = [c for c in self._cases.values() if c.tenant_id == tenant_id]
            cases.sort(key=lambda x: x.created_at, reverse=True)
            return cases

    def create_tenant_case(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "HIGH",
        amount: float = 0.0,
    ) -> TenantCase:
        with self._lock:
            case_id = f"CASE-{tenant_id.replace('tenant-', '').upper()}-{uuid.uuid4().hex[:4].upper()}"
            case = TenantCase(
                case_id=case_id,
                tenant_id=tenant_id,
                title=title,
                description=description,
                severity=severity,
                amount=amount,
                status="OPEN",
                created_at=datetime.now(timezone.utc),
            )
            self._cases[case_id] = case
            return case

    def record_request(
        self,
        is_authenticated: bool = False,
        is_service: bool = False,
        is_rate_limited: bool = False,
        tenant_id: Optional[str] = None,
        latency_ms: float = 1.0,
    ):
        with self._lock:
            self._metrics_counts["total_requests"] += 1
            if is_authenticated:
                self._metrics_counts["authenticated_requests"] += 1
            if is_service:
                self._metrics_counts["service_requests"] += 1
            if is_rate_limited:
                self._metrics_counts["rate_limited_requests"] += 1

            tenant_key = tenant_id if tenant_id else ("authenticated" if is_authenticated else "unauthenticated")
            self._tenant_traffic[tenant_key] += 1

            self._metrics_counts["latencies"].append(latency_ms)
            if len(self._metrics_counts["latencies"]) > 100:
                self._metrics_counts["latencies"] = self._metrics_counts["latencies"][-100:]

    def get_metrics(self) -> GatewayMetrics:
        with self._lock:
            all_tenants = set(c.tenant_id for c in self._cases.values())
            lats = self._metrics_counts["latencies"]
            avg_lat = sum(lats) / len(lats) if lats else 1.2

            return GatewayMetrics(
                total_requests=self._metrics_counts["total_requests"],
                authenticated_requests=self._metrics_counts["authenticated_requests"],
                service_requests=self._metrics_counts["service_requests"],
                rate_limited_requests=self._metrics_counts["rate_limited_requests"],
                rate_limit_blocks=self._metrics_counts["rate_limited_requests"],
                active_tenants_count=len(all_tenants),
                tenant_traffic_distribution=dict(self._tenant_traffic),
                avg_latency_ms=round(avg_lat, 2),
            )


# Global singleton instance
gateway_store = GatewayStore()
