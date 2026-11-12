"""
Tests for Amazon Bedrock GenAI Investigation Assistant.
"""
import pytest
from genai.bedrock_assistant import BedrockInvestigationAssistant


def test_bedrock_assistant_mock_synthesis():
    """Verify mock synthesis produces grounded report with required fields."""
    assistant = BedrockInvestigationAssistant(mock_mode=True)

    txn = {
        "transaction_id": "TXN-DEMO-99",
        "amount": 87500.0,
        "currency": "INR",
        "risk_score": 0.8325,
        "risk_level": "HIGH",
    }
    evidence = {
        "avg_amount_24h": 12500.0,
        "amount_deviation": 7.0,
        "transaction_count_5m": 4,
        "new_device": True,
        "location_change": True,
    }

    report = assistant.generate_investigation_summary(
        case_id="CASE-DEMO-99",
        transaction=txn,
        evidence=evidence,
    )

    assert report is not None
    assert len(report.executive_summary) > 20
    assert len(report.key_evidence) >= 2
    assert len(report.recommended_actions) >= 2
    assert len(report.alternative_explanations) >= 1
    assert "7.0x" in report.executive_summary or "7.0" in report.key_evidence[0]

    # Verify ethical guardrail: No automated declaration of guilt
    summary_lower = report.executive_summary.lower()
    assert "guilty" not in summary_lower
    assert "convicted" not in summary_lower
