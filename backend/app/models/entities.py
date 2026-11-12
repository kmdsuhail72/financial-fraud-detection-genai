"""
SQLAlchemy ORM Entities for FinGuard AI
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Numeric, DateTime, ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Role(Base):
    __tablename__ = "roles"
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(String(50), ForeignKey("roles.id", ondelete="RESTRICT"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    role = relationship("Role", back_populates="users")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(50), primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    risk_segment = Column(String(50), default="STANDARD")
    kyc_status = Column(String(50), default="VERIFIED")
    country = Column(String(10), default="IN")
    city = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    accounts = relationship("Account", back_populates="customer")


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    account_type = Column(String(50), nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    opened_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(64), primary_key=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    merchant_id = Column(String(100))
    merchant_category = Column(String(100))
    channel = Column(String(50), nullable=False)
    location_country = Column(String(10))
    location_city = Column(String(100))
    device_id = Column(String(100))
    ip_address = Column(String(45))
    is_international = Column(Boolean, default=False, nullable=False)
    transaction_timestamp = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="transactions")
    prediction = relationship("FraudPrediction", back_populates="transaction", uselist=False)
    case = relationship("InvestigationCase", back_populates="transaction", uselist=False)


class FraudPrediction(Base):
    __tablename__ = "fraud_predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(64), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    model_version = Column(String(50), nullable=False)
    xgboost_prob = Column(Numeric(6, 4), nullable=False)
    isoforest_score = Column(Numeric(6, 4), nullable=False)
    unified_risk_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False)
    feature_snapshot = Column(JSONB, nullable=False)
    inference_latency_ms = Column(Numeric(8, 2))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="prediction")


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    id = Column(String(64), primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False)
    status = Column(String(50), default="OPEN", nullable=False)
    priority = Column(String(20), default="HIGH", nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    transaction = relationship("Transaction", back_populates="case")
    evidence = relationship("InvestigationEvidence", back_populates="case")
    ai_report = relationship("AIInvestigationReport", back_populates="case", uselist=False)
    decisions = relationship("InvestigatorDecision", back_populates="case")


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(50), default="RULE_ENGINE", nullable=False)
    confidence_score = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    case = relationship("InvestigationCase", back_populates="evidence")


class AIInvestigationReport(Base):
    __tablename__ = "ai_investigation_reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False)
    bedrock_model_id = Column(String(100), nullable=False)
    executive_summary = Column(Text, nullable=False)
    extracted_evidence = Column(JSONB, nullable=False)
    recommended_actions = Column(JSONB, nullable=False)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    generation_latency_ms = Column(Numeric(8, 2))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    case = relationship("InvestigationCase", back_populates="ai_report")


class InvestigatorDecision(Base):
    __tablename__ = "investigator_decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False)
    investigator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision = Column(String(50), nullable=False)
    action_taken = Column(String(100), nullable=False)
    notes = Column(Text, nullable=False)
    decision_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    case = relationship("InvestigationCase", back_populates="decisions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_name = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    previous_state = Column(JSONB)
    new_state = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id = Column(String(100), primary_key=True)
    model_type = Column(String(50), nullable=False)
    s3_artifact_uri = Column(String(255), nullable=False)
    metrics = Column(JSONB, nullable=False)
    hyperparameters = Column(JSONB)
    is_active = Column(Boolean, default=False, nullable=False)
    trained_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    deployed_at = Column(DateTime(timezone=True))
