"""
FinGuard AI — Phase 30: Regulatory Report Validation Engine.
Performs structural, consistency, and statutory deadline checks on SAR/STR submissions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from regulatory_reporting.models import (
    RegulatoryReport,
    ReportValidationResult,
    ValidationErrorItem,
)


def validate_regulatory_report(report: RegulatoryReport) -> ReportValidationResult:
    """
    Validates a SAR/STR report against regulatory submission standards:
    1. Checks required fields (Customer, Narrative, Category, Amount)
    2. Enforces minimum narrative depth (>= 20 characters)
    3. Detects duplicate transaction references
    4. Detects duplicate evidence references
    5. Validates non-empty transaction linking
    6. Identifies expired filing deadlines
    """
    errors: List[ValidationErrorItem] = []
    now = datetime.now(timezone.utc)

    # 1. Customer Identification
    if not report.customer_id or not report.customer_id.strip():
        errors.append(
            ValidationErrorItem(field="customer_id", message="Customer ID is mandatory for regulatory filing.")
        )
    if not report.customer_name or not report.customer_name.strip():
        errors.append(
            ValidationErrorItem(field="customer_name", message="Customer legal name is mandatory for regulatory filing.")
        )

    # 2. Suspicion Narrative
    if not report.suspicion_narrative or len(report.suspicion_narrative.strip()) < 20:
        errors.append(
            ValidationErrorItem(
                field="suspicion_narrative",
                message="Suspicion narrative must be at least 20 characters detailing the suspicious pattern.",
            )
        )

    # 3. Offense Category
    if not report.primary_offense_category or not report.primary_offense_category.strip():
        errors.append(
            ValidationErrorItem(
                field="primary_offense_category",
                message="Primary predicate offense category is required.",
            )
        )

    # 4. Transaction References
    if not report.transaction_ids or len(report.transaction_ids) == 0:
        errors.append(
            ValidationErrorItem(
                field="transaction_ids",
                message="At least one suspicious transaction reference must be attached to the filing.",
            )
        )
    else:
        # Check duplicate transaction references
        duplicates = [tx for tx in report.transaction_ids if report.transaction_ids.count(tx) > 1]
        if duplicates:
            unique_dupes = list(set(duplicates))
            errors.append(
                ValidationErrorItem(
                    field="transaction_ids",
                    message=f"Duplicate transaction reference(s) detected: {', '.join(unique_dupes)}.",
                )
            )

    # 5. Evidence References (Check for duplicates)
    if report.evidence_ids:
        dupe_ev = [ev for ev in report.evidence_ids if report.evidence_ids.count(ev) > 1]
        if dupe_ev:
            unique_dupe_ev = list(set(dupe_ev))
            errors.append(
                ValidationErrorItem(
                    field="evidence_ids",
                    message=f"Duplicate evidence reference(s) detected: {', '.join(unique_dupe_ev)}.",
                )
            )

    # 6. Suspicious Amount
    if report.total_suspicious_amount <= 0:
        errors.append(
            ValidationErrorItem(
                field="total_suspicious_amount",
                message="Total suspicious amount must be greater than zero.",
            )
        )

    # 7. Deadline Check (Warning)
    if report.filing_deadline and now > report.filing_deadline:
        errors.append(
            ValidationErrorItem(
                field="filing_deadline",
                message=f"Statutory filing deadline ({report.filing_deadline.isoformat()}) has passed.",
                severity="WARNING",
            )
        )

    # Only severity == "ERROR" makes the report structurally invalid
    is_valid = not any(e.severity == "ERROR" for e in errors)

    return ReportValidationResult(is_valid=is_valid, errors=errors, checked_at=now)

