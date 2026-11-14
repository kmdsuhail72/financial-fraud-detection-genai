"""
FinGuard AI — Enterprise Disaster Recovery & Business Continuity Models
Schemas for RTO/RPO objectives, compliance assessments, backup manifests,
failover proposals, and regional health monitoring.
"""
from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ServicePriority(str, Enum):
    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Medium
    P4 = "P4"  # Low


class AssessmentStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    BREACHED = "BREACHED"
    AT_RISK = "AT_RISK"


class FailoverAction(str, Enum):
    STAY_PRIMARY = "STAY_PRIMARY"
    EXECUTE_FAILOVER = "EXECUTE_FAILOVER"
    BLOCKED_LAG_EXCEEDED = "BLOCKED_LAG_EXCEEDED"
    BLOCKED_SECONDARY_NOT_READY = "BLOCKED_SECONDARY_NOT_READY"


class ServiceTarget(BaseModel):
    service_id: str
    name: str
    target_rto_min: int  # Target Recovery Time Objective in minutes
    target_rpo_min: int  # Target Recovery Point Objective in minutes
    priority: ServicePriority
    tier: str
    description: str

    model_config = ConfigDict(extra="allow")


class RecoveryAssessment(BaseModel):
    service_id: str
    name: str
    target_rto_min: int
    target_rpo_min: int
    measured_rto_min: float
    measured_rpo_min: float
    rto_compliant: bool
    rpo_compliant: bool
    overall_compliant: bool
    gap_rto_min: float
    gap_rpo_min: float
    status: AssessmentStatus
    evaluated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    model_config = ConfigDict(extra="allow")


class BackupFileEntry(BaseModel):
    filename: str
    size_bytes: int
    sha256_checksum: str
    created_at: str
    status: str = "VERIFIED"

    model_config = ConfigDict(extra="allow")


class BackupManifest(BaseModel):
    manifest_id: str = Field(default_factory=lambda: f"mnf-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    backup_type: str = "FULL"  # FULL | INCREMENTAL
    source_region: str = "ap-south-1"
    replica_region: str = "ap-southeast-1"
    files: List[BackupFileEntry] = Field(default_factory=list)
    total_size_bytes: int = 0
    overall_sha256: str = ""
    verified: bool = True

    model_config = ConfigDict(extra="allow")


class BackupVerificationResult(BaseModel):
    manifest_id: str
    valid: bool
    files_checked: int
    mismatches: List[str] = Field(default_factory=list)
    verification_time_ms: float
    message: str

    model_config = ConfigDict(extra="allow")


class FailoverProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"fop-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    primary_region: str = "ap-south-1"
    secondary_region: str = "ap-southeast-1"
    primary_healthy: bool
    secondary_ready: bool
    replication_lag_min: float
    max_allowed_rpo_min: int = 5
    approved_for_failover: bool
    recommended_action: FailoverAction
    rationale: str
    human_approval_required: bool = True
    authorized_by: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class RegionHealth(BaseModel):
    region: str
    role: str  # PRIMARY | SECONDARY
    status: str  # HEALTHY | DEGRADED | UNREACHABLE
    latency_ms: float
    eks_cluster_status: str
    dynamodb_status: str
    s3_crr_status: str
    last_checked: str

    model_config = ConfigDict(extra="allow")


class DRHealthResponse(BaseModel):
    status: str
    primary_region: str
    secondary_region: str
    s3_crr_active: bool
    dynamodb_pitr_active: bool
    targets_count: int
    active_failover_proposal: Optional[FailoverProposal] = None
    timestamp: str

    model_config = ConfigDict(extra="allow")

