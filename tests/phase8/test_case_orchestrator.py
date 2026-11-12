"""
Tests for SQS Case Orchestrator Lambda Handler.
"""
import json
from unittest.mock import MagicMock
import pytest

from lambda_case_orchestrator.handler import CaseOrchestrator
from investigation.case_store import CaseStore
from genai.bedrock_assistant import BedrockInvestigationAssistant


def test_case_orchestrator_alert_processing():
    """Verify SQS alert invokes Bedrock assistant and creates investigation case."""
    mock_store = CaseStore(in_memory_fallback=True)
    mock_bedrock = BedrockInvestigationAssistant(mock_mode=True)

    orchestrator = CaseOrchestrator(case_store=mock_store, bedrock_assistant=mock_bedrock)

    alert_payload = {
        "event_type": "HIGH_RISK_FRAUD_ALERT",
        "transaction_id": "TXN-ALERT-001",
        "account_id": "ACC-9001",
        "customer_id": "CUS-9001",
        "amount": 95000.0,
        "currency": "INR",
        "risk_score": 0.88,
        "risk_level": "HIGH",
        "evidence": {
            "amount": 95000.0,
            "avg_amount_24h": 10000.0,
            "transaction_count_5m": 3,
            "new_device": True,
        },
    }

    # First execution: Case created
    case = orchestrator.process_alert(alert_payload)
    assert case is not None
    assert case.transaction_id == "TXN-ALERT-001"
    assert case.amount == 95000.0
    assert case.ai_summary is not None
    assert len(case.ai_summary.executive_summary) > 0

    # Second execution: Duplicate transaction ID is safely deduplicated
    case_dup = orchestrator.process_alert(alert_payload)
    assert case_dup.case_id == case.case_id


def test_sqs_event_batch_with_partial_failure():
    """Verify SQS event handler correctly reports partial failures."""
    mock_store = CaseStore(in_memory_fallback=True)
    mock_bedrock = BedrockInvestigationAssistant(mock_mode=True)
    orchestrator = CaseOrchestrator(case_store=mock_store, bedrock_assistant=mock_bedrock)

    valid_alert = {
        "transaction_id": "TXN-SQS-OK",
        "amount": 45000.0,
    }

    event = {
        "Records": [
            {
                "messageId": "msg-ok",
                "body": json.dumps(valid_alert),
            },
            {
                "messageId": "msg-fail",
                "body": "INVALID_NON_JSON_BODY",
            },
        ]
    }

    response = orchestrator.process_sqs_event(event)
    assert "batchItemFailures" in response
    failures = response["batchItemFailures"]
    assert len(failures) == 1
    assert failures[0]["itemIdentifier"] == "msg-fail"
