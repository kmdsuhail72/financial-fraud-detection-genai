"""
FinGuard AI — Phase 7 Real-Time Scoring Lambda Configuration.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringConfig:
    aws_region: str = os.getenv("AWS_REGION", "ap-south-1")
    sagemaker_endpoint_name: str = os.getenv("SAGEMAKER_ENDPOINT_NAME", "finguard-fraud-endpoint-dev")
    dynamodb_decisions_table: str = os.getenv("DYNAMODB_TABLE_DECISIONS", "finguard-fraud-decisions")
    sqs_investigation_queue_url: str = os.getenv("SQS_INVESTIGATION_QUEUE_URL", "")
    risk_threshold_high: float = float(os.getenv("RISK_THRESHOLD_HIGH", "0.60"))
    risk_threshold_review: float = float(os.getenv("RISK_THRESHOLD_REVIEW", "0.35"))
    weight_fraud_probability: float = float(os.getenv("WEIGHT_FRAUD_PROBABILITY", "0.65"))
    weight_anomaly_score: float = float(os.getenv("WEIGHT_ANOMALY_SCORE", "0.35"))
    decision_ttl_days: int = int(os.getenv("DECISION_TTL_DAYS", "90"))
