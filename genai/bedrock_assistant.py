"""
FinGuard AI — Amazon Bedrock GenAI Investigation Assistant (Phase 8).

Generates evidence-grounded case summaries, risk indicator explanations,
alternative benign hypotheses, and recommended investigative checks
using the Amazon Bedrock Converse API.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from genai.guardrails.schema_validator import validate_bedrock_response
from investigation.models import BedrockAISummary

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are FinGuard AI's Senior Financial Crime Investigation Assistant, integrated with Amazon Bedrock.
Your objective is to assist accredited human investigators by synthesizing transaction details, velocity features, and risk model signals into a clear, grounded case investigation report.

CRITICAL OPERATIONAL RULES:
1. Grounding in Evidence: Strictly ground all claims in the structured transaction and customer baseline data provided. Do NOT hallucinate past incidents, customer confessions, or unverified claims.
2. Separation of Concerns: You DO NOT declare a customer guilty, block an account, or reject payments. The human investigator retains sole adjudicative authority. Frame all findings as "potential risk indicators" and "observed deviations".
3. Quantify Discrepancies: State explicit numerical comparisons (e.g. "Amount ₹87,500 is 7.0x the customer 24h baseline of ₹12,500").
4. Strict JSON Output: Respond ONLY with a valid JSON object matching the requested schema.
"""


class BedrockInvestigationAssistant:
    """Invokes Amazon Bedrock Converse API to produce evidence-grounded investigation reports."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
        bedrock_client: Optional[Any] = None,
        mock_mode: bool = False,
    ):
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-south-1")
        self.mock_mode = mock_mode

        if not self.mock_mode and bedrock_client is None:
            try:
                self.client = boto3.client("bedrock-runtime", region_name=self.region_name)
            except Exception as e:
                logger.warning("Failed to initialize bedrock-runtime client (%s). Enabling mock mode.", e)
                self.client = None
                self.mock_mode = True
        else:
            self.client = bedrock_client

    def generate_investigation_summary(
        self,
        case_id: str,
        transaction: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> BedrockAISummary:
        """
        Synthesizes an investigation report using Bedrock Converse API or mock fallback.
        """
        if self.mock_mode or self.client is None:
            return self._generate_mock_summary(case_id, transaction, evidence)

        prompt_text = self._build_prompt(case_id, transaction, evidence)

        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt_text}],
                    }
                ],
                system=[{"text": DEFAULT_SYSTEM_PROMPT}],
                inferenceConfig={
                    "maxTokens": 1024,
                    "temperature": 0.1,
                    "topP": 0.9,
                },
            )

            # Extract output text
            output_msg = response["output"]["message"]["content"][0]["text"]
            is_valid, parsed_report, err = validate_bedrock_response(output_msg)

            if is_valid and parsed_report:
                return BedrockAISummary(
                    executive_summary=parsed_report.executive_summary,
                    key_evidence=parsed_report.key_evidence,
                    recommended_actions=parsed_report.recommended_actions,
                    alternative_explanations=[
                        "Legitimate high-value family or emergency purchase",
                        "Authorized device upgrade or domestic travel",
                    ],
                    confidence_rationale=parsed_report.confidence_rationale or "High confidence grounded in quantitative baseline deviations.",
                    evidence_limitations="Features reflect rolling 24-hour window; long-term customer behavioral variance should be examined.",
                    model_id=self.model_id,
                )
            else:
                logger.warning("Bedrock response failed schema validation (%s). Falling back to grounded template.", err)
                return self._generate_mock_summary(case_id, transaction, evidence)

        except ClientError as exc:
            logger.error("Bedrock Converse invocation error: %s. Using deterministic fallback.", exc)
            return self._generate_mock_summary(case_id, transaction, evidence)

    def _build_prompt(
        self,
        case_id: str,
        transaction: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> str:
        amount = transaction.get("amount", evidence.get("amount", 0.0))
        currency = transaction.get("currency", "INR")
        avg_24h = evidence.get("avg_amount_24h", amount)
        deviation = evidence.get("amount_deviation", round(amount / max(avg_24h, 1.0), 2))
        vel_5m = evidence.get("transaction_count_5m", 0)
        new_dev = evidence.get("new_device", False)
        loc_chg = evidence.get("location_change", False)

        return f"""Analyze the following flagged financial transaction case and synthesize an objective, evidence-based investigation report.

CASE INFORMATION:
- Case ID: {case_id}
- Transaction ID: {transaction.get('transaction_id', 'UNKNOWN')}
- Unified Risk Score: {transaction.get('risk_score', evidence.get('risk_score', 0.85))}
- Risk Tier: {transaction.get('risk_level', 'HIGH')}

TRANSACTION & EVIDENCE:
- Amount: {currency} {amount}
- Customer 24h Baseline Average: {currency} {avg_24h}
- Amount Deviation: {deviation}x above 24h average
- Velocity (last 5 min): {vel_5m} transactions
- New Device Flag: {new_dev}
- Location Mismatch Flag: {loc_chg}

Respond in strict JSON with fields: case_id, risk_level, executive_summary, key_evidence, recommended_actions, confidence_rationale.
"""

    def _generate_mock_summary(
        self,
        case_id: str,
        transaction: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> BedrockAISummary:
        """Generates a strictly grounded, deterministic investigation summary for offline/test environments."""
        amount = transaction.get("amount", evidence.get("amount", 25000.0))
        currency = transaction.get("currency", "INR")
        avg_24h = evidence.get("avg_amount_24h", 5000.0)
        deviation = evidence.get("amount_deviation", round(amount / max(avg_24h, 1.0), 2))
        vel_5m = evidence.get("transaction_count_5m", evidence.get("transaction_count_5m_prior", 2))
        new_device = bool(evidence.get("new_device", evidence.get("new_device_flag", False)))
        loc_change = bool(evidence.get("location_change", evidence.get("home_city_mismatch", False)))

        key_evidence = [
            f"Transaction amount ({currency} {amount:,.2f}) is {deviation:.1f}x the customer's 24-hour historical baseline ({currency} {avg_24h:,.2f}).",
            f"Transaction velocity burst: {vel_5m} transactions observed in the prior 5-minute rolling window.",
        ]
        if new_device:
            key_evidence.append("Observed transaction from an unrecognized device ID for this account.")
        if loc_change:
            key_evidence.append("Geographic anomaly detected: Transaction originated outside customer's primary residential region.")

        recommended_actions = [
            "Contact cardholder via primary registered phone for two-factor transaction confirmation.",
            "Verify whether customer recently traveled or purchased a new mobile device.",
            "Inspect correlated transactions on this card within the past 24 hours for testing activity.",
            "Temporarily restrict outbound high-velocity transfer limits if confirmation cannot be obtained.",
        ]

        alternative_explanations = [
            "Legitimate high-value emergency or festive shopping purchase by the account holder.",
            "Customer recently purchased and configured a replacement mobile device.",
        ]

        summary = (
            f"Transaction {transaction.get('transaction_id', 'UNKNOWN')} was flagged by the FinGuard AI risk engine "
            f"due to a {deviation:.1f}x monetary surge relative to the customer's 24-hour historical average, "
            f"combined with an elevated velocity burst of {vel_5m} transactions within 5 minutes. "
            f"{'Unrecognized device credentials and location anomalies further elevate risk.' if (new_device or loc_change) else ''} "
            f"Human analyst review is recommended to confirm authorization before applying account restrictions."
        )

        return BedrockAISummary(
            executive_summary=summary,
            key_evidence=key_evidence,
            recommended_actions=recommended_actions,
            alternative_explanations=alternative_explanations,
            confidence_rationale="High confidence grounded in quantitative baseline deviations and velocity indicators.",
            evidence_limitations="Behavioral profile relies on rolling 24h baseline; long-term seasonal variance not yet incorporated.",
            model_id=self.model_id,
        )

