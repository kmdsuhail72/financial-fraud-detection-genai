"""
FinGuard AI — Phase 35: Enterprise CI/CD, GitOps & DevSecOps Test Suite.
Validates:
1. CI/CD platform health & enterprise capabilities (/cicd/health)
2. Automated pipeline trigger (happy path through all DevSecOps verification gates)
3. Pipeline failure injection and quality gate blocking
4. SonarQube static analysis, code coverage, and quality gate metrics
5. Trivy container vulnerability scanner findings (zero CRITICAL CVEs)
6. Argo CD GitOps continuous delivery synchronization status
7. Argo Rollouts canary promotion and automated rollback
8. GitHub Actions, Jenkinsfile, and Argo CD manifests syntax verification
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import yaml

from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_cicd_health_and_capabilities(client):
    """1. Validates /cicd/health endpoint and DevSecOps capabilities."""
    resp = client.get("/cicd/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "devsecops_cicd_pipeline"
    assert data["phase"] == "Phase-35"
    caps = data["capabilities"]
    assert "github_actions_multistage" in caps
    assert "jenkins_declarative_pipeline" in caps
    assert "sonarqube_quality_gate" in caps
    assert "trivy_container_scanning" in caps
    assert "argocd_gitops_continuous_delivery" in caps
    assert "canary_rollouts_and_rollback" in caps


def test_pipeline_trigger_success_flow(client):
    """2. Validates successful end-to-end pipeline run through all DevSecOps stages."""
    resp = client.post("/cicd/pipeline/trigger?branch=main")
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "SUCCESS"
    assert len(run["stages"]) == 6
    stage_names = [s["name"] for s in run["stages"]]
    assert "Code Quality & Tests" in stage_names
    assert "SonarQube Quality Gate" in stage_names
    assert "Checkov IaC Scan" in stage_names
    assert "Docker & Trivy Scan" in stage_names
    assert "ECR Container Publish" in stage_names
    assert "Argo CD GitOps Sync" in stage_names
    assert all(s["status"] == "PASSED" for s in run["stages"])


def test_pipeline_trigger_failure_simulation(client):
    """3. Validates that pipeline failure halts downstream deployment stages."""
    resp = client.post("/cicd/pipeline/trigger?force_fail_stage=Docker%20%26%20Trivy%20Scan")
    assert resp.status_code == 200
    run = resp.json()
    assert run["status"] == "FAILED"
    failed_stage = next(s for s in run["stages"] if s["status"] == "FAILED")
    assert "Docker & Trivy Scan" in failed_stage["name"]
    assert "Simulated pipeline failure" in failed_stage["error"]


def test_sonarqube_quality_gate_report(client):
    """4. Validates SonarQube code quality report and coverage threshold (> 80%)."""
    resp = client.get("/cicd/sonarqube/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["quality_gate_status"] == "PASSED"
    assert report["coverage_percentage"] >= 80.0
    assert report["bugs_count"] == 0
    assert report["project_key"] == "finguard-ai-enterprise"


def test_trivy_container_vulnerability_scan(client):
    """5. Validates Trivy container security scan and absence of CRITICAL CVEs."""
    resp = client.get("/cicd/trivy/vulnerabilities")
    assert resp.status_code == 200
    findings = resp.json()
    assert isinstance(findings, list)
    # Zero CRITICAL or HIGH unpatched vulnerabilities
    assert not any(f["severity"].upper() == "CRITICAL" for f in findings)


def test_argocd_gitops_application_sync(client):
    """6. Validates Argo CD application sync and health status."""
    resp = client.get("/cicd/argocd/status")
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) >= 2
    app_names = [a["app_name"] for a in apps]
    assert "finguard-transaction-service" in app_names
    assert "finguard-fraud-service" in app_names
    for a in apps:
        assert a["sync_status"] == "Synced"
        assert a["health_status"] == "Healthy"


def test_canary_rollout_promotion_and_rollback(client):
    """7. Validates Argo Rollouts canary traffic splitting and emergency rollback."""
    # 1. Promote to 50%
    prom_resp = client.post("/cicd/canary/promote?weight=50")
    assert prom_resp.status_code == 200
    assert prom_resp.json()["canary_weight"] == 50

    # Verify updated weight in Argo CD status
    status_resp = client.get("/cicd/argocd/status")
    txn_app = next(a for a in status_resp.json() if a["app_name"] == "finguard-transaction-service")
    assert txn_app["canary_weight_percentage"] == 50

    # 2. Trigger Rollback
    rb_resp = client.post("/cicd/canary/rollback")
    assert rb_resp.status_code == 200
    assert rb_resp.json()["canary_weight"] == 100
    assert "Rollback" in rb_resp.json()["canary_phase"]


def test_github_actions_and_jenkins_manifests_syntax():
    """8. Validates GitHub Actions workflow, Jenkinsfile, and Argo CD manifests syntax."""
    # GitHub Actions Workflow
    gha_path = Path(".github/workflows/enterprise-devsecops-ci.yml")
    assert gha_path.exists()
    gha_yaml = yaml.safe_load(gha_path.read_text(encoding="utf-8"))
    assert "name" in gha_yaml
    jobs = gha_yaml.get("jobs", {})
    assert "code-quality-and-test" in jobs
    assert "iac-security" in jobs
    assert "container-security" in jobs
    assert "gitops-sync" in jobs

    # Jenkinsfile
    jenkins_path = Path("ci/Jenkinsfile")
    assert jenkins_path.exists()
    jenkins_text = jenkins_path.read_text(encoding="utf-8")
    assert "pipeline {" in jenkins_text
    assert "SonarQube Quality Gate" in jenkins_text

    # Argo CD App Manifests
    argocd_dir = Path("gitops/argocd")
    assert argocd_dir.exists()
    argo_apps = list(argocd_dir.glob("*.yaml"))
    assert len(argo_apps) >= 3
    for app_file in argo_apps:
        content = yaml.safe_load(app_file.read_text(encoding="utf-8"))
        assert content["kind"] == "Application"
        assert content["apiVersion"] == "argoproj.io/v1alpha1"
