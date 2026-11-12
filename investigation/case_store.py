"""
FinGuard AI — DynamoDB Investigation Case Store (Phase 8).

Manages storage, retrieval, deduplication, and audit tracking for fraud investigation cases.
Supports seamless offline in-memory fallback for local API testing without AWS.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from investigation.models import (
    AnalystNote,
    AuditTrailEntry,
    CasePriority,
    CaseStatus,
    CaseUpdateRequest,
    InvestigationCase,
)
from lambda_scoring.dynamodb_decisions import decimal_to_float, float_to_decimal

logger = logging.getLogger(__name__)


class CaseStore:
    """DynamoDB repository for FinGuard AI fraud investigation cases."""

    def __init__(
        self,
        table_name: Optional[str] = None,
        region_name: Optional[str] = None,
        dynamodb_resource: Optional[Any] = None,
        in_memory_fallback: bool = True,
    ):
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_CASES", "finguard-investigation-cases")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-south-1")
        self.in_memory_fallback = in_memory_fallback
        self._memory_cases: Dict[str, Dict[str, Any]] = {}
        self._txn_to_case_id: Dict[str, str] = {}
        self.table = None

        if dynamodb_resource is not None:
            self.table = dynamodb_resource.Table(self.table_name)
        else:
            try:
                dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self.table = dynamodb.Table(self.table_name)
                # Quick check if table exists
                self.table.load()
            except Exception as e:
                if self.in_memory_fallback:
                    logger.info("DynamoDB table '%s' not accessible (%s). Using local in-memory case store.", self.table_name, e)
                    self.table = None
                else:
                    raise

    def create_case(self, case: InvestigationCase) -> bool:
        """
        Creates a new investigation case. Enforces deduplication by transaction_id.

        Returns:
            True if newly created, False if a case already exists for this transaction.
        """
        # Audit trail initialization
        if not case.audit_trail:
            case.audit_trail.append(
                AuditTrailEntry(
                    action="CASE_CREATED",
                    performed_by="SYSTEM",
                    details={"risk_level": case.risk_level, "risk_score": case.risk_score},
                )
            )

        case_dict = case.model_dump()

        if self.table is None:
            # In-memory storage
            if case.transaction_id in self._txn_to_case_id:
                logger.warning("Duplicate case rejected for transaction %s", case.transaction_id)
                return False
            self._memory_cases[case.case_id] = case_dict
            self._txn_to_case_id[case.transaction_id] = case.case_id
            logger.info("Created case %s in memory for txn %s", case.case_id, case.transaction_id)
            return True

        # DynamoDB write
        dynamo_item = float_to_decimal(case_dict)
        try:
            self.table.put_item(
                Item=dynamo_item,
                ConditionExpression="attribute_not_exists(case_id)",
            )
            logger.info("Successfully persisted case %s to DynamoDB", case.case_id)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning("Case %s already exists in DynamoDB", case.case_id)
                return False
            logger.error("Failed to put case %s: %s", case.case_id, exc)
            raise

    def get_case(self, case_id: str) -> Optional[InvestigationCase]:
        """Retrieves a single case by case_id."""
        if self.table is None:
            raw = self._memory_cases.get(case_id)
            return InvestigationCase.model_validate(raw) if raw else None

        try:
            resp = self.table.get_item(Key={"case_id": case_id})
            item = resp.get("Item")
            if not item:
                return None
            clean_item = decimal_to_float(item)
            return InvestigationCase.model_validate(clean_item)
        except ClientError as exc:
            logger.error("Failed to get case %s: %s", case_id, exc)
            raise

    def get_case_by_transaction_id(self, transaction_id: str) -> Optional[InvestigationCase]:
        """Finds an existing case linked to transaction_id."""
        if self.table is None:
            case_id = self._txn_to_case_id.get(transaction_id)
            return self.get_case(case_id) if case_id else None

        try:
            # Query GSI TransactionIndex
            resp = self.table.query(
                IndexName="TransactionIndex",
                KeyConditionExpression="transaction_id = :tid",
                ExpressionAttributeValues={":tid": transaction_id},
            )
            items = resp.get("Items", [])
            if items:
                clean_item = decimal_to_float(items[0])
                return InvestigationCase.model_validate(clean_item)
            return None
        except Exception as e:
            logger.warning("TransactionIndex query error (%s). Falling back to scan.", e)
            # Scan fallback
            resp = self.table.scan(
                FilterExpression="transaction_id = :tid",
                ExpressionAttributeValues={":tid": transaction_id},
            )
            items = resp.get("Items", [])
            if items:
                return InvestigationCase.model_validate(decimal_to_float(items[0]))
            return None

    def list_cases(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InvestigationCase]:
        """Lists investigation cases with filtering and pagination."""
        if self.table is None:
            all_cases = [InvestigationCase.model_validate(c) for c in self._memory_cases.values()]
            if status:
                all_cases = [c for c in all_cases if c.status.value == status or c.status == status]
            if priority:
                all_cases = [c for c in all_cases if c.priority.value == priority or c.priority == priority]
            # Sort newest first
            all_cases.sort(key=lambda c: c.created_at, reverse=True)
            return all_cases[offset : offset + limit]

        try:
            filter_exprs = []
            expr_vals = {}
            if status:
                filter_exprs.append("#s = :status")
                expr_vals[":status"] = status
            if priority:
                filter_exprs.append("priority = :prio")
                expr_vals[":prio"] = priority

            scan_kwargs = {"Limit": limit}
            if filter_exprs:
                scan_kwargs["FilterExpression"] = " AND ".join(filter_exprs)
                scan_kwargs["ExpressionAttributeValues"] = expr_vals
            if status:
                scan_kwargs["ExpressionAttributeNames"] = {"#s": "status"}

            resp = self.table.scan(**scan_kwargs)
            items = resp.get("Items", [])
            cases = [InvestigationCase.model_validate(decimal_to_float(i)) for i in items]
            cases.sort(key=lambda c: c.created_at, reverse=True)
            return cases
        except ClientError as exc:
            logger.error("Failed to list cases: %s", exc)
            raise

    def update_case(
        self,
        case_id: str,
        updates: CaseUpdateRequest,
        performed_by: str = "analyst@example.com",
    ) -> Optional[InvestigationCase]:
        """Applies analyst updates, notes, and audit events to an existing case."""
        case = self.get_case(case_id)
        if not case:
            return None

        now_str = datetime.now(timezone.utc).isoformat()
        audit_details = {}

        if updates.status and updates.status != case.status:
            audit_details["old_status"] = case.status.value
            audit_details["new_status"] = updates.status.value
            case.status = updates.status
            case.audit_trail.append(
                AuditTrailEntry(
                    action="STATUS_CHANGED",
                    performed_by=performed_by,
                    details={"status": updates.status.value},
                )
            )

        if updates.assigned_to is not None and updates.assigned_to != case.assigned_to:
            audit_details["assigned_to"] = updates.assigned_to
            case.assigned_to = updates.assigned_to
            case.audit_trail.append(
                AuditTrailEntry(
                    action="ANALYST_ASSIGNED",
                    performed_by=performed_by,
                    details={"assigned_to": updates.assigned_to},
                )
            )

        if updates.priority and updates.priority != case.priority:
            case.priority = updates.priority
            audit_details["priority"] = updates.priority.value

        if updates.resolution_action:
            case.resolution_action = updates.resolution_action
            case.status = CaseStatus.RESOLVED
            if updates.resolution_notes:
                case.resolution_notes = updates.resolution_notes
            case.audit_trail.append(
                AuditTrailEntry(
                    action="CASE_RESOLVED",
                    performed_by=performed_by,
                    details={
                        "action": updates.resolution_action.value,
                        "notes": updates.resolution_notes,
                    },
                )
            )

        if updates.note:
            note_entry = AnalystNote(
                author=performed_by,
                content=updates.note,
                timestamp=now_str,
            )
            case.notes.append(note_entry)
            case.audit_trail.append(
                AuditTrailEntry(
                    action="NOTE_ADDED",
                    performed_by=performed_by,
                    details={"note_id": note_entry.note_id},
                )
            )

        case.updated_at = now_str

        # Persist updated case
        if self.table is None:
            self._memory_cases[case_id] = case.model_dump()
            return case

        dynamo_item = float_to_decimal(case.model_dump())
        self.table.put_item(Item=dynamo_item)
        return case
