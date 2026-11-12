"""
Unit test for Bedrock GenAI Schema Validation & Guardrails.
"""
from genai.guardrails.schema_validator import validate_bedrock_response
from genai.schemas.investigation_report import BedrockInvestigationReport


def test_valid_bedrock_response():
    raw_json = """
    {
      "case_id": "CASE-20261112-00001",
      "risk_level": "CRITICAL",
      "executive_summary": "Transaction flagged due to sudden 7x amount surge above customer 24h baseline.",
      "key_evidence": [
        "Transaction amount is 7.0x above 24h baseline",
        "New device DEV-45002 observed"
      ],
      "recommended_actions": [
        "Perform step-up verification via phone call",
        "Place temporary hold on account"
      ],
      "confidence_rationale": "High confidence based on verified deviations."
    }
    """
    is_valid, report, error = validate_bedrock_response(raw_json)
    assert is_valid is True
    assert error is None
    assert isinstance(report, BedrockInvestigationReport)
    assert report.risk_level.value == "CRITICAL"


def test_markdown_wrapped_bedrock_response():
    raw_markdown = """```json
    {
      "case_id": "CASE-20261112-00002",
      "risk_level": "HIGH",
      "executive_summary": "Multiple international payments detected in short window.",
      "key_evidence": [
        "3 transactions within 10 minutes across different countries"
      ],
      "recommended_actions": [
        "Block international transactions flag"
      ]
    }
    ```"""
    is_valid, report, error = validate_bedrock_response(raw_markdown)
    assert is_valid is True
    assert report.case_id == "CASE-20261112-00002"


def test_invalid_bedrock_response():
    malformed = "{ invalid_json: true "
    is_valid, report, error = validate_bedrock_response(malformed)
    assert is_valid is False
    assert report is None
    assert "Failed to decode JSON" in error
