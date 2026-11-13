"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) Store.
Thread-safe storage for customer risk profiles, AML monitoring transactions, cases, and SAR investigation drafts.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from aml.models import (
    AMLAlert,
    AMLCaseStatus,
    AMLInvestigationCase,
    AMLMetricsResponse,
    AMLRuleType,
    AMLTransaction,
    CaseActivityEntry,
    CaseNote,
    CustomerRiskProfile,
    CustomerRiskTier,
    SARInvestigationDraft,
)
from aml.profiler import CustomerRiskProfiler
from aml.rules_engine import AMLRulesEngine


class AMLStore:
    """Thread-safe AML data store managing transactions, alerts, customer profiles, and investigation cases."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._profiles: Dict[str, CustomerRiskProfile] = {}
        self._history: Dict[str, List[AMLTransaction]] = {}
        self._cases: Dict[str, AMLInvestigationCase] = {}
        self._alerts: List[AMLAlert] = []
        self._sar_drafts: Dict[str, SARInvestigationDraft] = {}
        self._rules_engine = AMLRulesEngine()
        self._profiler = CustomerRiskProfiler()

    def get_or_create_profile(
        self,
        customer_id: str,
        name: Optional[str] = None,
        country: str = "US",
        pep_flag: bool = False,
    ) -> CustomerRiskProfile:
        with self._lock:
            if customer_id not in self._profiles:
                now = datetime.now(timezone.utc)
                self._profiles[customer_id] = CustomerRiskProfile(
                    customer_id=customer_id,
                    name=name or f"Customer {customer_id}",
                    risk_tier=CustomerRiskTier.LOW,
                    risk_score=15,
                    account_type="CHECKING",
                    country=country,
                    pep_flag=pep_flag,
                    risk_factors=[],
                    created_at=now,
                    updated_at=now,
                )
            return self._profiles[customer_id]

    def process_transaction(
        self, transaction: AMLTransaction
    ) -> Tuple[List[AMLAlert], Optional[AMLInvestigationCase], CustomerRiskProfile]:
        with self._lock:
            cid = transaction.customer_id
            profile = self.get_or_create_profile(cid)

            # Retrieve customer transaction history
            cust_txns = self._history.setdefault(cid, [])

            # Evaluate rules engine
            alerts = self._rules_engine.evaluate_transaction(transaction, cust_txns, profile)

            # Record transaction in history
            cust_txns.append(transaction)

            # Update customer risk profile
            updated_profile = self._profiler.calculate_risk(
                profile, alerts, incremental_volume=transaction.amount
            )

            case: Optional[AMLInvestigationCase] = None

            # If alerts triggered, create or escalate investigation case
            if alerts:
                for a in alerts:
                    self._alerts.append(a)

                # Find open case or create a new one
                existing_open = [
                    c for c in self._cases.values()
                    if c.customer_id == cid and c.status in (AMLCaseStatus.NEW, AMLCaseStatus.UNDER_INVESTIGATION)
                ]

                now = datetime.now(timezone.utc)
                if existing_open:
                    case = existing_open[0]
                    case.alerts.extend(alerts)
                    case.risk_score = updated_profile.risk_score
                    case.risk_tier = updated_profile.risk_tier
                    case.updated_at = now
                    case.history.append(
                        CaseActivityEntry(
                            actor="AML_RULES_ENGINE",
                            action="ALERTS_APPENDED",
                            details={
                                "alert_count": len(alerts),
                                "rules": [a.rule_type.value for a in alerts],
                                "transaction_id": transaction.transaction_id,
                            },
                        )
                    )
                else:
                    case_id = f"AML-CASE-{uuid.uuid4().hex[:8].upper()}"
                    initial_history = [
                        CaseActivityEntry(
                            actor="AML_RULES_ENGINE",
                            action="CASE_CREATED",
                            details={
                                "initial_alerts": [a.rule_type.value for a in alerts],
                                "transaction_id": transaction.transaction_id,
                                "trigger_amount": transaction.amount,
                            },
                        )
                    ]
                    case = AMLInvestigationCase(
                        case_id=case_id,
                        customer_id=cid,
                        status=AMLCaseStatus.NEW,
                        alerts=alerts,
                        risk_score=updated_profile.risk_score,
                        risk_tier=updated_profile.risk_tier,
                        notes=[],
                        evidence_refs=[f"TXN-{transaction.transaction_id}"],
                        created_at=now,
                        updated_at=now,
                        history=initial_history,
                    )
                    self._cases[case_id] = case

            return alerts, case, updated_profile

    def get_case(self, case_id: str) -> Optional[AMLInvestigationCase]:
        with self._lock:
            return self._cases.get(case_id)

    def list_cases(
        self,
        status: Optional[AMLCaseStatus] = None,
        risk_tier: Optional[CustomerRiskTier] = None,
        customer_id: Optional[str] = None,
    ) -> List[AMLInvestigationCase]:
        with self._lock:
            results = []
            for c in self._cases.values():
                if status and c.status != status:
                    continue
                if risk_tier and c.risk_tier != risk_tier:
                    continue
                if customer_id and c.customer_id != customer_id:
                    continue
                results.append(c)
            return sorted(results, key=lambda x: x.created_at, reverse=True)

    def update_case_status(
        self,
        case_id: str,
        new_status: AMLCaseStatus,
        actor: str = "aml.analyst",
        notes: Optional[str] = None,
    ) -> AMLInvestigationCase:
        with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise KeyError(f"AML case '{case_id}' not found.")

            now = datetime.now(timezone.utc)
            old_status = case.status
            case.status = new_status
            case.updated_at = now

            case.history.append(
                CaseActivityEntry(
                    actor=actor,
                    action="STATUS_CHANGED",
                    details={
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "notes": notes or "",
                    },
                )
            )
            return case

    def add_case_note(
        self, case_id: str, author: str, content: str
    ) -> AMLInvestigationCase:
        with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise KeyError(f"AML case '{case_id}' not found.")

            now = datetime.now(timezone.utc)
            note = CaseNote(author=author, created_at=now, content=content)
            case.notes.append(note)
            case.updated_at = now

            case.history.append(
                CaseActivityEntry(
                    actor=author,
                    action="NOTE_ADDED",
                    details={"preview": content[:60]},
                )
            )
            return case

    def generate_sar_draft(
        self,
        case_id: str,
        prepared_by: str = "aml.investigator",
        disposition: str = "RECOMMEND_SAR_FILING",
    ) -> SARInvestigationDraft:
        with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise KeyError(f"AML case '{case_id}' not found.")

            profile = self._profiles.get(case.customer_id)
            now = datetime.now(timezone.utc)
            draft_id = f"SAR-{uuid.uuid4().hex[:8].upper()}"

            violating_rules = list(set(a.rule_type.value for a in case.alerts))
            total_suspicious = sum(a.trigger_amount for a in case.alerts)

            # Build narrative
            narrative = (
                f"Suspicious Activity Report (SAR) Investigation Draft for Subject {case.customer_id} "
                f"({profile.name if profile else 'Retail Cardholder'}). Subject engaged in repeated transaction patterns "
                f"violating AML monitoring thresholds, specifically: {', '.join(violating_rules)}. "
                f"Total cumulative suspicious volume flagged during the review window is ${total_suspicious:,.2f} USD."
            )

            citations = [f"ALERT-{a.alert_id}" for a in case.alerts] + case.evidence_refs

            # Markdown report
            md_lines = [
                f"# FinGuard AI — Suspicious Activity Report (SAR) Investigation Draft",
                f"**Draft ID:** `{draft_id}` | **Case ID:** `{case_id}` | **Generated:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
                f"**Lead AML Investigator:** `{prepared_by}` | **Subject ID:** `{case.customer_id}`",
                f"**Recommended Disposition:** `{disposition}`",
                "",
                "---",
                "",
                "## 1. Suspicious Activity Narrative",
                narrative,
                "",
                "## 2. Customer Risk Profile & Subject Information",
                f"- **Customer Name:** {profile.name if profile else 'N/A'}",
                f"- **Customer Risk Score:** `{profile.risk_score if profile else 0}/100` ({case.risk_tier.value})",
                f"- **PEP Designation:** `{profile.pep_flag if profile else False}`",
                f"- **Jurisdiction:** `{profile.country if profile else 'US'}`",
                "",
                "## 3. Flagged Suspicious Transaction Patterns",
            ]
            for a in case.alerts:
                md_lines.append(
                    f"- **[{a.rule_type.value}]** (Severity: `{a.severity}`) — Amount: `${a.trigger_amount:,.2f}`. *{a.description}*"
                )

            md_lines.extend([
                "",
                "## 4. Evidence References & Audit Citations",
            ])
            for c in citations:
                md_lines.append(f"- `{c}`")

            md_lines.extend([
                "",
                "## 5. Compliance Sign-Off & Legal Notice",
                "*This document represents an internal investigatory draft for compliance committee review.*",
                f"- **Signed By:** `{prepared_by}`",
                f"- **Timestamp:** `{now.isoformat()}`",
            ])

            draft = SARInvestigationDraft(
                draft_id=draft_id,
                case_id=case_id,
                customer_id=case.customer_id,
                prepared_by=prepared_by,
                generated_at=now,
                suspicious_activity_summary=narrative,
                violating_patterns=violating_rules,
                total_suspicious_amount=total_suspicious,
                evidence_citations=citations,
                recommended_disposition=disposition,
                report_markdown="\n".join(md_lines),
            )

            self._sar_drafts[draft_id] = draft
            case.status = AMLCaseStatus.REPORT_PREPARED
            case.history.append(
                CaseActivityEntry(
                    actor=prepared_by,
                    action="SAR_DRAFT_GENERATED",
                    details={"draft_id": draft_id, "disposition": disposition},
                )
            )
            return draft

    def get_metrics(self) -> AMLMetricsResponse:
        with self._lock:
            total_txns = sum(len(txns) for txns in self._history.values())
            total_alerts = len(self._alerts)
            active_cases = sum(
                1 for c in self._cases.values()
                if c.status in (AMLCaseStatus.NEW, AMLCaseStatus.UNDER_INVESTIGATION, AMLCaseStatus.ESCALATED)
            )

            risk_dist = {
                CustomerRiskTier.LOW.value: 0,
                CustomerRiskTier.MEDIUM.value: 0,
                CustomerRiskTier.HIGH.value: 0,
                CustomerRiskTier.CRITICAL.value: 0,
            }
            for p in self._profiles.values():
                risk_dist[p.risk_tier.value] = risk_dist.get(p.risk_tier.value, 0) + 1

            alerts_by_rule = {
                AMLRuleType.LARGE_CASH_TRANSACTION.value: 0,
                AMLRuleType.POSSIBLE_STRUCTURING.value: 0,
                AMLRuleType.RAPID_INFLOW_OUTFLOW.value: 0,
                AMLRuleType.HIGH_VELOCITY.value: 0,
            }
            for a in self._alerts:
                alerts_by_rule[a.rule_type.value] = alerts_by_rule.get(a.rule_type.value, 0) + 1

            return AMLMetricsResponse(
                total_monitored_transactions=total_txns,
                total_alerts_detected=total_alerts,
                active_investigation_cases=active_cases,
                customer_risk_distribution=risk_dist,
                alerts_by_rule_type=alerts_by_rule,
                avg_case_resolution_time_hours=4.5,
            )

    def clear(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._history.clear()
            self._cases.clear()
            self._alerts.clear()
            self._sar_drafts.clear()

