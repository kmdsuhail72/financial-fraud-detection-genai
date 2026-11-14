"""
FinGuard AI — Enterprise Disaster Recovery & Business Continuity Router
Provides REST APIs for RTO/RPO targets, compliance assessments, failover planning,
backup integrity verification, and multi-region health.
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from disaster_recovery.backup import backup_manager
from disaster_recovery.models import (
    BackupManifest,
    BackupVerificationResult,
    DRHealthResponse,
    FailoverProposal,
    RecoveryAssessment,
    RegionHealth,
    ServiceTarget,
)
from disaster_recovery.service import dr_service

dr_router = APIRouter(prefix="/dr", tags=["Disaster Recovery & Business Continuity"])


class AssessRecoveryRequest(BaseModel):
    service_id: str = Field(..., json_schema_extra={"example": "transaction-ingestion"})
    measured_rto_min: float = Field(..., ge=0, json_schema_extra={"example": 22.0})
    measured_rpo_min: float = Field(..., ge=0, json_schema_extra={"example": 3.0})

    model_config = ConfigDict(extra="allow")


class FailoverPlanRequest(BaseModel):
    primary_healthy: bool = Field(False, description="Whether the primary Mumbai region is healthy")
    secondary_ready: bool = Field(True, description="Whether the secondary Singapore region is ready")
    replication_lag_min: float = Field(2.0, ge=0, description="Measured data replication lag in minutes")
    authorized_by: Optional[str] = Field(None, description="Operator or on-call engineer authorizing review")

    model_config = ConfigDict(extra="allow")


class VerifyBackupRequest(BaseModel):
    manifest: Optional[BackupManifest] = None
    inject_corruption: bool = False

    model_config = ConfigDict(extra="allow")


@dr_router.get("/health", response_model=DRHealthResponse)
def get_dr_health():
    """Health check for the disaster recovery subsystem."""
    return dr_service.get_health()


@dr_router.get("/targets", response_model=List[ServiceTarget])
def get_dr_targets():
    """Lists all approved enterprise RTO/RPO objectives by service."""
    return dr_service.list_targets()


@dr_router.get("/targets/{service_id}", response_model=ServiceTarget)
def get_dr_target(service_id: str):
    """Retrieves target RTO/RPO for a specific service."""
    target = dr_service.get_target(service_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found in DR targets.",
        )
    return target


@dr_router.post("/assess", response_model=RecoveryAssessment)
def assess_recovery(payload: AssessRecoveryRequest):
    """Evaluates actual recovery measurements against defined RTO/RPO targets."""
    assessment = dr_service.assess_recovery(
        service_id=payload.service_id,
        measured_rto_min=payload.measured_rto_min,
        measured_rpo_min=payload.measured_rpo_min,
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{payload.service_id}' not found in DR targets.",
        )
    return assessment


@dr_router.post("/failover/plan", response_model=FailoverProposal)
def generate_failover_proposal(payload: FailoverPlanRequest):
    """Generates an advisory failover proposal based on health and replication lag."""
    return dr_service.generate_failover_plan(
        primary_healthy=payload.primary_healthy,
        secondary_ready=payload.secondary_ready,
        replication_lag_min=payload.replication_lag_min,
        authorized_by=payload.authorized_by,
    )


@dr_router.post("/backup/verify", response_model=BackupVerificationResult)
def verify_backup_integrity(payload: VerifyBackupRequest):
    """Verifies SHA-256 checksums across files in a backup manifest."""
    manifest = payload.manifest or backup_manager.create_sample_manifest(inject_corruption=payload.inject_corruption)
    return dr_service.verify_backup_manifest(manifest)


@dr_router.get("/regions", response_model=List[RegionHealth])
def get_regional_health():
    """Retrieves live health status across primary Mumbai and secondary Singapore regions."""
    return dr_service.get_regional_status()


@dr_router.get("/manifest/sample", response_model=BackupManifest)
def get_sample_manifest(corrupt: bool = Query(False)):
    """Generates a sample backup manifest for demonstration or testing."""
    return backup_manager.create_sample_manifest(inject_corruption=corrupt)
