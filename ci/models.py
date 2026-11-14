"""
FinGuard AI — Phase 35: Enterprise CI/CD, GitOps & DevSecOps Models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class StageStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    SKIPPED = "SKIPPED"


class PipelineStage(BaseModel):
    name: str
    status: StageStatus = StageStatus.PASSED
    duration_seconds: float = 12.5
    error: Optional[str] = None
    output_summary: str = "Stage executed successfully"

    model_config = ConfigDict(extra="allow")


class PipelineRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run-{uuid.uuid4().hex[:8]}")
    branch: str = "main"
    commit_sha: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: PipelineStatus = PipelineStatus.SUCCESS
    stages: List[PipelineStage] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_duration_seconds: float = 64.0

    model_config = ConfigDict(extra="allow")


class SonarQubeReport(BaseModel):
    quality_gate_status: str = "PASSED"  # PASSED / FAILED
    coverage_percentage: float = 94.2
    code_smells: int = 0
    bugs_count: int = 0
    vulnerabilities_count: int = 0
    security_hotspots_reviewed: float = 100.0
    duplications_percentage: float = 0.8
    project_key: str = "finguard-ai-enterprise"

    model_config = ConfigDict(extra="allow")


class TrivyFinding(BaseModel):
    vulnerability_id: str
    package: str
    installed_version: str
    fixed_version: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str

    model_config = ConfigDict(extra="allow")


class ArgoCdAppStatus(BaseModel):
    app_name: str
    sync_status: str = "Synced"  # Synced, OutOfSync
    health_status: str = "Healthy"  # Healthy, Progressing, Degraded
    target_revision: str = "HEAD"
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    canary_weight_percentage: int = 100
    canary_phase: str = "Stable"  # Canary (20%), Canary (50%), Stable (100%)

    model_config = ConfigDict(extra="allow")


class DevSecOpsMetrics(BaseModel):
    total_pipeline_runs: int
    successful_runs: int
    failed_runs: int
    avg_pipeline_duration_seconds: float
    sonarqube_quality_gate: str
    critical_vulnerabilities_count: int
    argocd_sync_status: str
    canary_traffic_split: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")
