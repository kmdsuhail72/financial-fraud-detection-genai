"""
FinGuard AI Backend Application Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    APP_NAME: str = "FinGuard AI"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # AWS
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "finguard-data-dev"
    KINESIS_STREAM_NAME: str = "finguard-transactions-dev"

    # Database
    DATABASE_URL: str = "postgresql://finguard:finguard_secret@localhost:5432/finguard"

    # Risk Engine & Models
    MODEL_NAME: str = "xgboost"
    FRAUD_THRESHOLD: float = 0.80
    ANOMALY_THRESHOLD: float = 0.60
    RISK_WEIGHT_SUPERVISED: float = 0.65
    RISK_WEIGHT_ANOMALY: float = 0.35

    # Bedrock GenAI
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # Security & Auth
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_SECRET_KEY_MIN_32_CHARS"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # API
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]


settings = Settings()
