"""
FinGuard AI — Fraud Investigation Case Orchestrator Lambda (Phase 8).

Consumes high-risk investigation alerts from Amazon SQS,
deduplicates cases, requests evidence synthesis from Amazon Bedrock,
and registers new investigation cases in DynamoDB.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from genai.bedrock_assistant import BedrockInvestigationAssistant
from investigation.case_store import CaseStore
from investigation.models import (
    CasePriority,
    CaseStatus,
    InvestigationCase,
)

logger = logging.getLogger("finguard-case-orchestrator")
logger.setLevel(logging.INFO)


class CaseOrchestrator:
    """Orchestrates case creation and Bedrock GenAI synthesis from SQS alerts."""

    def __init__(
        self,
        case_store: Optional[CaseStore] = None,
        bedrock_assistant: Optional[BedrockInvestigationAssistant] = None,
    ):
        self.case_store = case_store or CaseStore()
        self.bedrock = bedrock_assistant or BedrockInvestigationAssistant()

    def process_alert(self, alert_data: Dict[str, Any]) -> Optional[InvestigationCase]:
        """Processes a single investigation alert payload."""
        txn_id = alert_data.get("transaction_id", "UNKNOWN")

        # 1. Deduplication: Check if case already exists for this transaction
        existing_case = self.case_store.get_case_by_transaction_id(txn_id)
        if existing_case:
            logger.info("Case %s already exists for transaction %s; skipping duplicate creation.", existing_case.case_id, txn_id)
            return existing_case

        # 2. Assign unique Case ID
        today_str = time.strftime("%Y%m%d", time.gmtime())
        short_id = uuid.uuid4().hex[:6].upper()
        case_id = f"CASE-{today_str}-{short_id}"

        # 3. Extract evidence features
        evidence = alert_data.get("evidence", alert_data)
        risk_score = float(alert_data.get("risk_score", 0.85))
        risk_level = alert_data.get("risk_level", "HIGH")

        # 4. Invoke Bedrock GenAI Assistant
        logger.info("Invoking Bedrock assistant for case %s (transaction: %s)", case_id, txn_id)
        ai_summary = self.bedrock.generate_investigation_summary(
            case_id=case_id,
            transaction=alert_data,
            evidence=evidence,
        )

        # 5. Build and persist InvestigationCase
        priority = CasePriority.CRITICAL if risk_score >= 0.80 else CasePriority.HIGH

        new_case = InvestigationCase(
            case_id=case_id,
            transaction_id=txn_id,
            account_id=alert_data.get("account_id", "ACC-UNKNOWN"),
            customer_id=alert_data.get("customer_id", "CUS-UNKNOWN"),
            amount=float(alert_data.get("amount", 0.0)),
            currency=alert_data.get("currency", "INR"),
            risk_score=risk_score,
            risk_level=risk_level,
            status=CaseStatus.OPEN,
            priority=priority,
            evidence=evidence,
            ai_summary=ai_summary,
        )

        saved = self.case_store.create_case(new_case)
        if saved:
            logger.info("Created investigation case %s for transaction %s", case_id, txn_id)
            return new_case
        return None

    def process_sqs_event(self, event: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """Handles SQS batch event with partial batch failure reporting."""
        records = event.get("Records", [])
        batch_failures = []
        logger.info("Processing SQS alert batch of %d records", len(records))

        for record in records:
            msg_id = record.get("messageId", "")
            try:
                body = record.get("body", "{}")
                alert_data = json.loads(body)
                self.process_alert(alert_data)
            except Exception as exc:
                logger.error("Failed processing SQS message %s: %s", msg_id, exc, exc_info=True)
                if msg_id:
                    batch_failures.append({"itemIdentifier": msg_id})

        return {"batchItemFailures": batch_failures}


# Global handler singleton
_ORCHESTRATOR: Optional[CaseOrchestrator] = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, List[Dict[str, str]]]:
    """AWS Lambda entrypoint for SQS case orchestrator."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = CaseOrchestrator()
    return _ORCHESTRATOR.process_sqs_event(event)

