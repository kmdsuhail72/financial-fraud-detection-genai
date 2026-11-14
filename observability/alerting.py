"""
FinGuard AI — SRE Alerting Engine
Evaluates alerting rules against Prometheus metrics and SLO budgets,
maintains active alerts, and associates alerts with SRE runbooks.
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional
from observability.models import (
    ActiveAlert,
    AlertRule,
    AlertSeverity,
    AlertState,
    RunbookItem,
)


class AlertManager:
    """Evaluates rules and manages active alert state."""

    def __init__(self) -> None:
        self._rules: List[AlertRule] = []
        self._active_alerts: Dict[str, ActiveAlert] = {}
        self._runbooks: Dict[str, RunbookItem] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        self._rules = [
            AlertRule(
                name="High5xxErrorRate",
                severity=AlertSeverity.CRITICAL,
                expr="sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) > 0.01",
                duration_minutes=2,
                description="FinGuard HTTP 5xx error rate exceeds 1% for more than 2 minutes.",
                runbook_url="/docs/sre-incident-runbook.md#high-5xx-error-rate",
            ),
            AlertRule(
                name="HighFraudScoringLatencyP95",
                severity=AlertSeverity.WARNING,
                expr="histogram_quantile(0.95, sum(rate(fraud_scoring_latency_seconds_bucket[5m])) by (le)) > 0.2",
                duration_minutes=5,
                description="Fraud scoring p95 latency exceeds 200ms for more than 5 minutes.",
                runbook_url="/docs/sre-incident-runbook.md#high-scoring-latency",
            ),
            AlertRule(
                name="ServiceInstanceDown",
                severity=AlertSeverity.CRITICAL,
                expr="finguard_service_up == 0",
                duration_minutes=1,
                description="FinGuard microservice instance or pod is unreachable.",
                runbook_url="/docs/sre-incident-runbook.md#pod-crashloop-or-unreachable",
            ),
            AlertRule(
                name="ErrorBudgetFastBurn",
                severity=AlertSeverity.WARNING,
                expr="slo:burn_rate:1h > 14.4",
                duration_minutes=15,
                description="1-hour error budget burn rate exceeds 14.4x (2% budget consumed in 1 hour).",
                runbook_url="/docs/sre-incident-runbook.md#error-budget-exhaustion",
            ),
        ]

        self._runbooks = {
            "rb-5xx": RunbookItem(
                id="rb-5xx",
                title="High 5xx Error Rate Triage & Rollback",
                severity=AlertSeverity.CRITICAL,
                trigger_condition="5xx error rate > 1% over 2 minutes",
                immediate_actions=[
                    "Check Argo CD deployment status and recent commits",
                    "Verify Kubernetes pod restart counts (`kubectl get pods -n finguard`)",
                    "Check CloudWatch Log Group `/aws/eks/finguard/services` for uncaught exceptions",
                ],
                investigation_steps=[
                    "Inspect trace spans with status_code=ERROR in OpenTelemetry explorer",
                    "Verify downstream database and Redis cache connectivity",
                    "Check ingress controller error logs",
                ],
                mitigation_steps=[
                    "Scale pod replicas if saturation: `kubectl scale deployment transaction-service -n finguard --replicas=6`",
                    "If a recent canary deployment caused failures, execute immediate automated rollback: `argo rollouts abort transaction-service`",
                ],
                rollback_command="kubectl rollout undo deployment/transaction-service -n finguard",
                escalation_contacts=["oncall-sre@finguard.ai", "+91-9876543210 (PagerDuty)"],
            ),
            "rb-latency": RunbookItem(
                id="rb-latency",
                title="Fraud Scoring p95 Latency Triage",
                severity=AlertSeverity.WARNING,
                trigger_condition="Fraud scoring p95 latency > 200ms",
                immediate_actions=[
                    "Inspect Bedrock GenAI & SageMaker endpoint invocation times",
                    "Check CPU and Memory utilization across ML scoring pods",
                    "Verify DynamoDB latency metrics in CloudWatch",
                ],
                investigation_steps=[
                    "Query Jaeger/OTel traces filtered by `service.name=fraud-scoring-service` and `duration > 200ms`",
                    "Check network latency between Gateway and scoring pods",
                ],
                mitigation_steps=[
                    "Trigger Horizontal Pod Autoscaler scale-out",
                    "Enable feature cache fallback in `ml/inference/predictor.py`",
                ],
                rollback_command="kubectl rollout undo deployment/fraud-service -n finguard",
                escalation_contacts=["mlops-team@finguard.ai"],
            ),
        }

    def list_rules(self) -> List[AlertRule]:
        return self._rules

    def list_runbooks(self) -> List[RunbookItem]:
        return list(self._runbooks.values())

    def get_runbook(self, runbook_id: str) -> Optional[RunbookItem]:
        return self._runbooks.get(runbook_id)

    def evaluate_rules(
        self,
        error_rate_5xx: float = 0.002,
        p95_latency_ms: float = 65.0,
        services_down: Optional[List[str]] = None,
        burn_rate_1h: float = 0.42,
    ) -> List[ActiveAlert]:
        """Evaluates active alerting criteria and synchronizes active alerts."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        alerts_firing: List[ActiveAlert] = []

        # 1. Check 5xx error rate
        if error_rate_5xx > 0.01:
            alt = ActiveAlert(
                alert_name="High5xxErrorRate",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                service="finguard-gateway",
                summary=f"5xx error rate is {round(error_rate_5xx * 100, 2)}% (threshold: > 1%)",
                started_at=now_str,
                labels={"severity": "CRITICAL", "service": "finguard-gateway"},
                annotations={"runbook": "rb-5xx"},
                runbook_url="/docs/sre-incident-runbook.md#high-5xx-error-rate",
            )
            alerts_firing.append(alt)
            self._active_alerts["High5xxErrorRate"] = alt
        elif "High5xxErrorRate" in self._active_alerts:
            self._active_alerts["High5xxErrorRate"].state = AlertState.RESOLVED

        # 2. Check p95 latency
        if p95_latency_ms > 200.0:
            alt = ActiveAlert(
                alert_name="HighFraudScoringLatencyP95",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                service="fraud-scoring-service",
                summary=f"Fraud scoring p95 latency is {round(p95_latency_ms, 1)}ms (threshold: > 200ms)",
                started_at=now_str,
                labels={"severity": "WARNING", "service": "fraud-scoring-service"},
                annotations={"runbook": "rb-latency"},
                runbook_url="/docs/sre-incident-runbook.md#high-scoring-latency",
            )
            alerts_firing.append(alt)
            self._active_alerts["HighFraudScoringLatencyP95"] = alt
        elif "HighFraudScoringLatencyP95" in self._active_alerts:
            self._active_alerts["HighFraudScoringLatencyP95"].state = AlertState.RESOLVED

        # 3. Check services down
        if services_down:
            for svc in services_down:
                alt = ActiveAlert(
                    alert_name="ServiceInstanceDown",
                    severity=AlertSeverity.CRITICAL,
                    state=AlertState.FIRING,
                    service=svc,
                    summary=f"Service instance '{svc}' is DOWN or unreachable",
                    started_at=now_str,
                    labels={"severity": "CRITICAL", "service": svc},
                    annotations={"runbook": "rb-5xx"},
                    runbook_url="/docs/sre-incident-runbook.md#pod-crashloop-or-unreachable",
                )
                alerts_firing.append(alt)
                self._active_alerts[f"ServiceInstanceDown_{svc}"] = alt

        # 4. Check burn rate
        if burn_rate_1h > 14.4:
            alt = ActiveAlert(
                alert_name="ErrorBudgetFastBurn",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                service="finguard-core",
                summary=f"1-hour error budget burn rate is {burn_rate_1h}x (threshold: > 14.4x)",
                started_at=now_str,
                labels={"severity": "WARNING", "service": "finguard-core"},
                runbook_url="/docs/sre-incident-runbook.md#error-budget-exhaustion",
            )
            alerts_firing.append(alt)
            self._active_alerts["ErrorBudgetFastBurn"] = alt
        elif "ErrorBudgetFastBurn" in self._active_alerts:
            self._active_alerts["ErrorBudgetFastBurn"].state = AlertState.RESOLVED

        return alerts_firing

    def list_active_alerts(self) -> List[ActiveAlert]:
        return [a for a in self._active_alerts.values() if a.state == AlertState.FIRING]


# Global singleton alert manager
alert_manager = AlertManager()
