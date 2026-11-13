"""
FinGuard AI — Real-Time Fraud Scoring, Investigation Management & Enterprise Security API.

Serves low-latency ML scoring inferences and provides full investigation case management
with Bedrock GenAI assistance, protected by Amazon Cognito JWT authentication,
role-based access control (RBAC), and immutable security audit logging.
"""
from __future__ import annotations

import logging
import os
import time

os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from genai.bedrock_assistant import BedrockInvestigationAssistant
from investigation.case_store import CaseStore
from investigation.models import (
    AnalystNote,
    AuditTrailEntry,
    BedrockAISummary,
    CaseListResponse,
    CasePriority,
    CaseStatus,
    CaseUpdateRequest,
    InvestigationCase,
    ResolutionAction,
)
from ml.inference.predictor import EnsembleFraudModel
from security.auth import AuthenticatedUser
from security.audit import SecurityAuditEvent, audit_logger
from security.dependencies import get_current_user, require_permission, require_roles
from security.roles import Permission, Role
from api.compliance_router import compliance_router
from api.soc_router import soc_router
from api.graph_router import graph_router
from api.threat_intel_router import threat_intel_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finguard-api")

# Global instances
CASE_STORE = CaseStore(in_memory_fallback=True)
BEDROCK_ASSISTANT = BedrockInvestigationAssistant()

MODEL_HOLDER: Dict[str, Any] = {
    "model": None,
    "model_path": None,
    "load_error": None,
}


def get_model() -> EnsembleFraudModel:
    """Retrieves or lazy-loads the model artifact from FINGUARD_MODEL_PATH."""
    model_path_str = os.getenv("FINGUARD_MODEL_PATH", "artifacts/model.joblib")
    model_path = Path(model_path_str)

    if MODEL_HOLDER["model"] is not None and MODEL_HOLDER["model_path"] == str(model_path):
        return MODEL_HOLDER["model"]

    if not model_path.exists():
        err_msg = f"Model artifact not found at: {model_path}. Please run training first or check FINGUARD_MODEL_PATH."
        MODEL_HOLDER["load_error"] = err_msg
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=err_msg)

    try:
        loaded = EnsembleFraudModel.load(str(model_path))
        MODEL_HOLDER["model"] = loaded
        MODEL_HOLDER["model_path"] = str(model_path)
        MODEL_HOLDER["load_error"] = None
        logger.info("Successfully loaded EnsembleFraudModel from %s (version: %s)", model_path, loaded.model_version)
        return loaded
    except Exception as exc:
        err_msg = f"Failed to load model from {model_path}: {exc}"
        MODEL_HOLDER["load_error"] = err_msg
        logger.error(err_msg, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)


def seed_demo_cases_if_empty():
    """Seeds initial demonstration cases so Swagger / UI displays realistic data immediately."""
    existing = CASE_STORE.list_cases(limit=1)
    if not existing:
        demo_case_1 = InvestigationCase(
            case_id="CASE-123",
            transaction_id="TXN-20261112-000001",
            account_id="ACC-100045",
            customer_id="CUS-200045",
            amount=87500.0,
            currency="INR",
            risk_score=0.8325,
            risk_level="HIGH",
            status=CaseStatus.OPEN,
            priority=CasePriority.CRITICAL,
            evidence={
                "amount": 87500.0,
                "avg_amount_24h": 12500.0,
                "amount_deviation": 7.0,
                "transaction_count_5m": 4,
                "new_device": True,
                "location_change": True,
            },
            ai_summary=BedrockAISummary(
                executive_summary="Transaction flagged due to sudden 7.0x amount surge above customer 24h baseline combined with new device registration and 4 transactions within 5 minutes.",
                key_evidence=[
                    "Transaction amount (₹87,500) is 7.0x the customer 24h average of ₹12,500.",
                    "Unrecognized device DEV-45002 observed for the first time.",
                    "High velocity burst: 4 transactions in 5 minutes.",
                ],
                recommended_actions=[
                    "Contact customer via registered mobile number for two-factor verification.",
                    "Review correlated IP 192.0.2.10 against threat intelligence lists.",
                    "Inspect customer login sessions in the prior 1 hour.",
                ],
                alternative_explanations=[
                    "Authorized high-value family appliance purchase on newly purchased smartphone.",
                ],
                confidence_rationale="High confidence grounded in quantitative baseline deviations.",
            ),
        )
        CASE_STORE.create_case(demo_case_1)
        logger.info("Seeded initial demo case CASE-123")


# Seed at module import time
try:
    seed_demo_cases_if_empty()
except Exception as e:
    logger.warning("Failed to seed initial demo cases: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Attempt non-blocking model load and seed initial cases at startup."""
    model_path = os.getenv("FINGUARD_MODEL_PATH", "artifacts/model.joblib")
    if Path(model_path).exists():
        try:
            get_model()
        except Exception as e:
            logger.warning("Startup model load deferred: %s", e)
    seed_demo_cases_if_empty()
    yield


app = FastAPI(
    title="FinGuard AI — Fraud Detection, Investigation & Security Governance Platform",
    version="1.0.0",
    description="Real-time transaction risk scoring, Bedrock GenAI investigation summaries, and analyst case management secured by Cognito JWT and RBAC.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance_router)
app.include_router(soc_router)
app.include_router(graph_router)
app.include_router(threat_intel_router)


# ==========================================
# Pydantic Schemas
# ==========================================
class TransactionScoreRequest(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "txn-demo"})
    features: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "example": {
                "amount": 12500,
                "currency": "INR",
                "channel": "mobile",
                "transaction_count_5m_prior": 4,
                "transaction_count_1h_prior": 12,
                "new_device_flag": True,
                "home_city_mismatch": False,
                "is_international": True,
            }
        },
    )
    model_config = ConfigDict(extra="allow")


class TransactionScoreResponse(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "txn-demo"})
    fraud_probability: float = Field(..., json_schema_extra={"example": 0.87})
    anomaly_score: float = Field(..., json_schema_extra={"example": 0.72})
    risk_score: float = Field(..., json_schema_extra={"example": 0.8325})
    risk_level: str = Field(..., json_schema_extra={"example": "HIGH"})
    classifier_threshold: float = Field(..., json_schema_extra={"example": 0.45})
    model_version: str = Field(..., json_schema_extra={"example": "v20261112T100000Z"})


class HealthCheckResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None
    model_path: Optional[str] = None
    case_store_status: str
    bedrock_model_id: str
    cognito_configured: bool
    audit_table: str
    uptime_seconds: float


class AssignCaseRequest(BaseModel):
    assigned_to: str = Field(..., json_schema_extra={"example": "investigator@finguard.internal"})


class AddNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, json_schema_extra={"example": "Customer verified overseas trip."})


class EscalateCaseRequest(BaseModel):
    reason: Optional[str] = Field(None, json_schema_extra={"example": "Suspicious rapid UPI burst exceeds standard threshold."})


class ResolveCaseRequest(BaseModel):
    resolution_action: ResolutionAction = Field(..., json_schema_extra={"example": "CONFIRMED_FRAUD"})
    resolution_notes: Optional[str] = Field(None, json_schema_extra={"example": "Card compromised and frozen."})


class ManageUserRoleRequest(BaseModel):
    user_id: str
    role: Role


START_TIME = time.time()


# ==========================================
# Health & Scoring Endpoints (Public / Operational)
# ==========================================
@app.get("/health", response_model=HealthCheckResponse)
def health():
    """System health, model status, and security configuration probe."""
    is_loaded = MODEL_HOLDER["model"] is not None
    version = MODEL_HOLDER["model"].model_version if is_loaded else None
    m_path = MODEL_HOLDER["model_path"]
    store_status = "DYNAMODB_CONNECTED" if CASE_STORE.table is not None else "IN_MEMORY_ACTIVE"
    cognito_configured = bool(os.getenv("COGNITO_USER_POOL_ID"))

    return HealthCheckResponse(
        status="HEALTHY",
        model_loaded=is_loaded,
        model_version=version,
        model_path=m_path,
        case_store_status=store_status,
        bedrock_model_id=BEDROCK_ASSISTANT.model_id,
        cognito_configured=cognito_configured,
        audit_table=audit_logger.table_name,
        uptime_seconds=round(time.time() - START_TIME, 2),
    )


@app.post("/score", response_model=TransactionScoreResponse)
def score_transaction(payload: Union[TransactionScoreRequest, Dict[str, Any]]):
    """Real-time fraud scoring for an inbound transaction."""
    model = get_model()
    if isinstance(payload, TransactionScoreRequest):
        txn_id = payload.transaction_id
        features = payload.features
    elif isinstance(payload, dict):
        txn_id = payload.get("transaction_id", f"txn-{int(time.time()*1000)}")
        features = payload.get("features", payload)
    else:
        raise HTTPException(status_code=400, detail="Invalid request body")

    try:
        result = model.predict_one(txn_id, features)
        return TransactionScoreResponse(**result)
    except Exception as exc:
        logger.error("Scoring failure for %s: %s", txn_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {exc}")


@app.post("/score/batch", response_model=List[TransactionScoreResponse])
def score_batch_transactions(transactions: List[TransactionScoreRequest]):
    """Batch scoring for high-throughput streaming batches."""
    model = get_model()
    try:
        txns_raw = [{"transaction_id": t.transaction_id, "features": t.features} for t in transactions]
        results = model.predict_batch(txns_raw)
        return [TransactionScoreResponse(**r) for r in results]
    except Exception as exc:
        logger.error("Batch scoring failure: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch inference error: {exc}")


@app.get("/model/metadata")
def get_model_metadata():
    """Retrieves model governance metadata, thresholds, and input schema."""
    model = get_model()
    return {
        "model_version": model.model_version,
        "model_type": model.model_type,
        "classifier_threshold": model.classifier_threshold,
        "thresholds": model.thresholds,
        "feature_manifest": model.preprocessor.export_manifest(),
    }


# ==========================================
# Protected Investigation Management Endpoints (Cognito JWT + RBAC)
# ==========================================

@app.get("/cases", response_model=CaseListResponse)
def list_cases(
    status: Optional[str] = Query(None, description="Filter by status: OPEN, IN_REVIEW, ESCALATED, RESOLVED, CLOSED"),
    priority: Optional[str] = Query(None, description="Filter by priority: CRITICAL, HIGH, MEDIUM, LOW"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Lists fraud investigation cases. Requires 'cases:view' (Admin, Investigator, Analyst, Auditor)."""
    cases = CASE_STORE.list_cases(status=status, priority=priority, limit=limit, offset=offset)
    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:view",
        resource_type="CASE_LIST",
        resource_id="ALL",
        status="SUCCESS",
        details={"status_filter": status, "priority_filter": priority, "count": len(cases)},
    )
    return CaseListResponse(total=len(cases), cases=cases)


@app.get("/cases/{case_id}", response_model=InvestigationCase)
def get_case(
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves full case details. Requires 'cases:view' (Admin, Investigator, Analyst, Auditor)."""
    case = CASE_STORE.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:view_detail",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
    )
    return case


@app.post("/cases/{case_id}/assign", response_model=InvestigationCase)
def assign_case(
    case_id: str,
    payload: AssignCaseRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ASSIGN_CASES)),
):
    """Assigns an investigation case to an analyst. Requires 'cases:assign' (Admin, Investigator)."""
    update_req = CaseUpdateRequest(assigned_to=payload.assigned_to)
    updated = CASE_STORE.update_case(
        case_id, update_req, performed_by=current_user.email or current_user.username
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:assign",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
        details={"assigned_to": payload.assigned_to},
    )
    return updated


@app.post("/cases/{case_id}/notes", response_model=InvestigationCase)
def add_case_note(
    case_id: str,
    payload: AddNoteRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ADD_NOTES)),
):
    """Appends an analyst note to a case. Requires 'cases:notes:add' (Admin, Investigator, Analyst)."""
    update_req = CaseUpdateRequest(note=payload.note)
    updated = CASE_STORE.update_case(
        case_id, update_req, performed_by=current_user.email or current_user.username
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:notes:add",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
        details={"note_preview": payload.note[:60]},
    )
    return updated


@app.post("/cases/{case_id}/escalate", response_model=InvestigationCase)
def escalate_case(
    case_id: str,
    payload: EscalateCaseRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ESCALATE_CASES)),
):
    """Escalates case to senior investigators. Requires 'cases:escalate' (Admin, Investigator, Analyst)."""
    note_text = f"ESCALATED: {payload.reason}" if payload.reason else "Case escalated for Senior AML/Fraud review."
    update_req = CaseUpdateRequest(status=CaseStatus.ESCALATED, note=note_text)
    updated = CASE_STORE.update_case(
        case_id, update_req, performed_by=current_user.email or current_user.username
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:escalate",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
        details={"reason": payload.reason},
    )
    return updated


@app.post("/cases/{case_id}/resolve", response_model=InvestigationCase)
def resolve_case(
    case_id: str,
    payload: ResolveCaseRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.RESOLVE_CASES)),
):
    """Records investigator resolution and binding verdict. Requires 'cases:resolve' (Admin, Investigator)."""
    update_req = CaseUpdateRequest(
        status=CaseStatus.RESOLVED,
        resolution_action=payload.resolution_action,
        resolution_notes=payload.resolution_notes,
    )
    updated = CASE_STORE.update_case(
        case_id, update_req, performed_by=current_user.email or current_user.username
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:resolve",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
        details={
            "action": payload.resolution_action.value,
            "notes": payload.resolution_notes,
        },
    )
    return updated


@app.patch("/cases/{case_id}", response_model=InvestigationCase)
def update_case(
    case_id: str,
    update_data: CaseUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Granular case updates with dynamic RBAC checks per updated field.
    """
    # Permission checks for modified fields
    if update_data.assigned_to is not None and Permission.ASSIGN_CASES not in current_user.permissions:
        audit_logger.log(
            actor_sub=current_user.sub,
            action="rbac:denied:cases:assign",
            resource_type="CASE",
            resource_id=case_id,
            status="DENIED",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role not authorized to assign cases. Requires 'cases:assign'.",
        )

    if update_data.resolution_action is not None and Permission.RESOLVE_CASES not in current_user.permissions:
        audit_logger.log(
            actor_sub=current_user.sub,
            action="rbac:denied:cases:resolve",
            resource_type="CASE",
            resource_id=case_id,
            status="DENIED",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role not authorized to resolve cases. Requires 'cases:resolve'.",
        )

    if update_data.status == CaseStatus.ESCALATED and Permission.ESCALATE_CASES not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role not authorized to escalate cases. Requires 'cases:escalate'.",
        )

    if update_data.note and Permission.ADD_NOTES not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role not authorized to add notes. Requires 'cases:notes:add'.",
        )

    performed_by = current_user.email or current_user.username
    updated = CASE_STORE.update_case(case_id, update_data, performed_by=performed_by)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:patch_update",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
        details={"fields_updated": [k for k, v in update_data.dict().items() if v is not None]},
    )
    return updated


@app.post("/cases", response_model=InvestigationCase, status_code=status.HTTP_201_CREATED)
def create_investigation_case(
    case_payload: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Manually creates an investigation case or triggers Bedrock synthesis. Requires Admin or Investigator role."""
    txn_id = case_payload.get("transaction_id", f"TXN-MANUAL-{int(time.time())}")
    existing = CASE_STORE.get_case_by_transaction_id(txn_id)
    if existing:
        return existing

    case_id = case_payload.get("case_id", f"CASE-{time.strftime('%Y%m%d')}-{int(time.time()%10000):04d}")
    evidence = case_payload.get("evidence", case_payload)

    # Synthesize AI summary via Bedrock
    ai_summary = BEDROCK_ASSISTANT.generate_investigation_summary(case_id, case_payload, evidence)

    new_case = InvestigationCase(
        case_id=case_id,
        transaction_id=txn_id,
        account_id=case_payload.get("account_id", "ACC-MANUAL"),
        customer_id=case_payload.get("customer_id", "CUS-MANUAL"),
        amount=float(case_payload.get("amount", 50000.0)),
        currency=case_payload.get("currency", "INR"),
        risk_score=float(case_payload.get("risk_score", 0.85)),
        risk_level=case_payload.get("risk_level", "HIGH"),
        status=CaseStatus.OPEN,
        priority=CasePriority.HIGH,
        evidence=evidence,
        ai_summary=ai_summary,
    )
    CASE_STORE.create_case(new_case)
    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="cases:create",
        resource_type="CASE",
        resource_id=case_id,
        status="SUCCESS",
    )
    return new_case


@app.get("/audit/logs", response_model=List[SecurityAuditEvent])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    actor_email: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_AUDIT)),
):
    """Retrieves immutable security audit logs. Requires 'audit:view' (Admin, Auditor)."""
    logs = audit_logger.list_logs(limit=limit, actor_email=actor_email)
    return logs


@app.post("/users/roles")
def manage_user_role(
    payload: ManageUserRoleRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Assigns security groups and roles to users. Requires 'users:manage' (Admin only)."""
    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="users:manage_role",
        resource_type="USER",
        resource_id=payload.user_id,
        status="SUCCESS",
        details={"assigned_role": payload.role.value},
    )
    return {
        "status": "SUCCESS",
        "user_id": payload.user_id,
        "assigned_role": payload.role.value,
        "updated_by": current_user.email or current_user.username,
    }
