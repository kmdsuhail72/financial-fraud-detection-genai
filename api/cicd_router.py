"""
FinGuard AI — Phase 35: Enterprise CI/CD, GitOps & DevSecOps Router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ci.models import (
    ArgoCdAppStatus,
    DevSecOpsMetrics,
    PipelineRun,
    SonarQubeReport,
    TrivyFinding,
)
from ci.service import devsecops_service

logger = logging.getLogger("finguard-cicd-api")

cicd_router = APIRouter(prefix="/cicd", tags=["DevSecOps & GitOps Pipeline"])


@cicd_router.get("/health", summary="DevSecOps & CI/CD Health Check")
def cicd_health():
    """Returns the operational status of the Enterprise CI/CD and GitOps platform."""
    return {
        "status": "healthy",
        "service": "devsecops_cicd_pipeline",
        "phase": "Phase-35",
        "capabilities": [
            "github_actions_multistage",
            "jenkins_declarative_pipeline",
            "sonarqube_quality_gate",
            "trivy_container_scanning",
            "checkov_iac_validation",
            "argocd_gitops_continuous_delivery",
            "canary_rollouts_and_rollback",
        ],
    }


@cicd_router.post(
    "/pipeline/trigger",
    response_model=PipelineRun,
    summary="Trigger Automated DevSecOps Pipeline",
)
def trigger_pipeline(
    branch: str = Query("main", description="Target Git branch"),
    commit_sha: Optional[str] = Query(None, description="Git commit hash"),
    force_fail_stage: Optional[str] = Query(None, description="Stage to simulate failure for testing"),
) -> PipelineRun:
    """Dispatches a simulated pipeline run through all DevSecOps verification stages."""
    return devsecops_service.trigger_pipeline(
        branch=branch,
        commit_sha=commit_sha,
        force_fail_stage=force_fail_stage,
    )


@cicd_router.get(
    "/pipeline/runs",
    response_model=List[PipelineRun],
    summary="List DevSecOps Pipeline Executions",
)
def list_pipeline_runs() -> List[PipelineRun]:
    """Retrieves chronological execution history for CI/CD runs."""
    return devsecops_service.list_runs()


@cicd_router.get(
    "/sonarqube/report",
    response_model=SonarQubeReport,
    summary="Inspect SonarQube Code Quality & Coverage Report",
)
def get_sonarqube_report() -> SonarQubeReport:
    """Returns static code analysis, quality gate status, and code coverage."""
    return devsecops_service.get_sonarqube_report()


@cicd_router.get(
    "/trivy/vulnerabilities",
    response_model=List[TrivyFinding],
    summary="Inspect Container Security Vulnerability Scan",
)
def get_trivy_vulnerabilities() -> List[TrivyFinding]:
    """Returns CVE scan results across container base images and dependencies."""
    return devsecops_service.get_trivy_findings()


@cicd_router.get(
    "/argocd/status",
    response_model=List[ArgoCdAppStatus],
    summary="Inspect Argo CD GitOps Application Synchronization",
)
def get_argocd_status() -> List[ArgoCdAppStatus]:
    """Returns cluster state, sync status, and active Canary deployment weights."""
    return devsecops_service.get_argocd_status()


@cicd_router.post(
    "/canary/promote",
    summary="Promote Canary Deployment Stage",
)
def promote_canary(
    weight: int = Query(50, description="Target canary traffic weight percentage (e.g. 20, 50, 100)"),
):
    """Promotes canary rollout traffic split (20% -> 50% -> 100% Stable)."""
    phase_str = f"Canary ({weight}%)" if weight < 100 else "Stable (100%)"
    return devsecops_service.update_canary_step(weight, phase_str)


@cicd_router.post(
    "/canary/rollback",
    summary="Rollback Canary Deployment",
)
def rollback_canary():
    """Immediately rolls back canary traffic to stable production release."""
    return devsecops_service.rollback_canary()


@cicd_router.get(
    "/metrics",
    response_model=DevSecOpsMetrics,
    summary="DevSecOps & GitOps Telemetry KPIs",
)
def get_metrics() -> DevSecOpsMetrics:
    """Aggregates pipeline frequency, quality gate pass rates, and security compliance."""
    return devsecops_service.get_metrics()
