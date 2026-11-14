"""
FinGuard AI — Phase 34: Containerization, Kubernetes Orchestration & Amazon EKS Test Suite.
Validates:
1. Transaction microservice endpoints & Kubernetes probes (/health, /ready, /live, /metrics)
2. Fraud-scoring microservice endpoints & inference (/health, /ready, /live, /score)
3. Multi-stage Dockerfiles & container security standards (non-root, healthchecks)
4. Docker Compose multi-service environment configuration
5. Kubernetes resource manifests syntax & securityContexts (Deployments, Services, HPA, PDB, NetworkPolicy, Ingress)
6. Helm chart metadata, schema, and values.yaml definitions
7. Prometheus scrape configurations and Grafana telemetry dashboards
8. AWS EKS Terraform foundation targeting Mumbai (ap-south-1)
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import yaml

from services.transaction_service import app as transaction_app
from services.fraud_service import app as fraud_app


def test_transaction_service_endpoints():
    """1. Validates Transaction service FastAPI probes & endpoints on port 8101."""
    client = TestClient(transaction_app)

    # Health
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["port"] == 8101

    # Kubernetes Probes
    assert client.get("/live").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/startup").status_code == 200

    # Prometheus metrics
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert "transaction_service_events_published" in metrics_resp.json()


def test_fraud_service_endpoints():
    """2. Validates Fraud-Scoring service FastAPI probes & risk scoring on port 8102."""
    client = TestClient(fraud_app)

    # Health & Probes
    assert client.get("/health").status_code == 200
    assert client.get("/live").status_code == 200
    assert client.get("/ready").status_code == 200

    # Real-time inference
    score_resp = client.post(
        "/score",
        json={
            "transaction_id": "TXN-TEST-100",
            "customer_id": "CUST-100",
            "amount": 150000.0,
            "home_city_mismatch": True,
            "new_device": True,
            "velocity_10m": 4,
        },
    )
    assert score_resp.status_code == 200
    data = score_resp.json()
    assert data["transaction_id"] == "TXN-TEST-100"
    assert data["risk_score"] >= 75.0
    assert data["decision"] == "BLOCK"
    assert len(data["reasons"]) >= 2


def test_dockerfiles_structure_and_security():
    """3. Validates multi-stage Dockerfiles and container hardening standards."""
    txn_dockerfile = Path("docker/Dockerfile.transaction").read_text(encoding="utf-8")
    fraud_dockerfile = Path("docker/Dockerfile.fraud").read_text(encoding="utf-8")

    for dockerfile, port in [(txn_dockerfile, "8101"), (fraud_dockerfile, "8102")]:
        # Multi-stage verification
        assert "AS builder" in dockerfile
        assert "AS runtime" in dockerfile

        # Non-root user creation and execution
        assert "useradd" in dockerfile or "appuser" in dockerfile
        assert "USER 10001:10001" in dockerfile or "USER appuser" in dockerfile

        # Healthcheck command
        assert "HEALTHCHECK" in dockerfile
        assert f"http://127.0.0.1:{port}/health" in dockerfile

        # Port exposition
        assert f"EXPOSE {port}" in dockerfile


def test_docker_compose_configuration():
    """4. Validates docker-compose.yml service declarations, ports, and healthchecks."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists()
    content = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    services = content.get("services", {})
    assert "transaction-service" in services
    assert "fraud-service" in services

    txn = services["transaction-service"]
    assert "8101:8101" in txn["ports"]
    assert "healthcheck" in txn
    assert "security_opt" in txn

    fraud = services["fraud-service"]
    assert "8102:8102" in fraud["ports"]
    assert "healthcheck" in fraud
    assert "security_opt" in fraud


def test_kubernetes_manifests_syntax():
    """5. Validates Kubernetes manifests syntax, securityContext, probes, and autoscaling."""
    k8s_dir = Path("k8s/base")
    assert k8s_dir.exists()

    manifest_files = list(k8s_dir.glob("*.yaml"))
    assert len(manifest_files) >= 8  # At least 8 manifests

    # Check Deployments for securityContext and probes
    txn_deploy = yaml.safe_load(Path("k8s/base/transaction-deployment.yaml").read_text(encoding="utf-8"))
    assert txn_deploy["kind"] == "Deployment"
    spec = txn_deploy["spec"]["template"]["spec"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    container = spec["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert "startupProbe" in container
    assert "livenessProbe" in container
    assert "readinessProbe" in container
    assert "resources" in container

    # Check HPA
    hpa_content = list(yaml.safe_load_all(Path("k8s/base/hpa.yaml").read_text(encoding="utf-8")))
    assert len(hpa_content) == 2
    assert all(doc["kind"] == "HorizontalPodAutoscaler" for doc in hpa_content)

    # Check Ingress
    ingress = yaml.safe_load(Path("k8s/base/ingress.yaml").read_text(encoding="utf-8"))
    assert ingress["kind"] == "Ingress"
    assert ingress["metadata"]["annotations"]["kubernetes.io/ingress.class"] == "alb"


def test_helm_chart_metadata_and_values():
    """6. Validates Helm Chart.yaml and values.yaml structure."""
    chart_file = Path("helm/finguard/Chart.yaml")
    values_file = Path("helm/finguard/values.yaml")
    assert chart_file.exists()
    assert values_file.exists()

    chart = yaml.safe_load(chart_file.read_text(encoding="utf-8"))
    assert chart["name"] == "finguard"
    assert chart["version"] == "1.0.0"
    assert chart["apiVersion"] == "v2"

    values = yaml.safe_load(values_file.read_text(encoding="utf-8"))
    assert "transactionService" in values
    assert "fraudService" in values
    assert values["transactionService"]["service"]["port"] == 8101
    assert values["fraudService"]["service"]["port"] == 8102
    assert values["transactionService"]["autoscaling"]["enabled"] is True


def test_monitoring_prometheus_and_grafana_configs():
    """7. Validates Prometheus scrape configs and Grafana starter dashboard."""
    prom_path = Path("monitoring/prometheus-scrape.yaml")
    grafana_path = Path("monitoring/grafana-dashboard.json")
    assert prom_path.exists()
    assert grafana_path.exists()

    prom = yaml.safe_load(prom_path.read_text(encoding="utf-8"))
    job_names = [j["job_name"] for j in prom["scrape_configs"]]
    assert "finguard-transaction-service" in job_names
    assert "finguard-fraud-service" in job_names

    with open(grafana_path, "r", encoding="utf-8") as f:
        grafana = json.load(f)
    assert "FinGuard AI" in grafana["title"]
    assert len(grafana["panels"]) >= 4


def test_terraform_eks_mumbai_configuration():
    """8. Validates AWS EKS Terraform code targeting Mumbai (ap-south-1)."""
    tf_dir = Path("infrastructure/terraform/phase34")
    assert tf_dir.exists()

    vars_content = Path("infrastructure/terraform/phase34/variables.tf").read_text(encoding="utf-8")
    assert 'default     = "ap-south-1"' in vars_content

    main_content = Path("infrastructure/terraform/phase34/main.tf").read_text(encoding="utf-8")
    assert "aws_eks_cluster" in main_content
    assert "aws_eks_node_group" in main_content
    assert "aws_eks_addon" in main_content
    assert "vpc_cni" in main_content
    assert "coredns" in main_content
