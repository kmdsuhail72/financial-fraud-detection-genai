# Phase 34 — Enterprise Containerization, Kubernetes Orchestration, Amazon EKS & Production Microservices Deployment

## 1. Overview
Phase 34 delivers production-ready containerization, Kubernetes orchestration, Helm packaging, and Amazon EKS infrastructure targeting AWS Mumbai (`ap-south-1`).

---

## 2. Implemented Architecture & Artifacts

### 2.1 Multi-Stage Containerization (`docker/`)
- `Dockerfile.transaction`: Multi-stage build producing an unprivileged runtime image running as non-root user `appuser` (UID 10001).
- `Dockerfile.fraud`: Hardened inference container with dropped Linux capabilities and healthcheck probes.

### 2.2 Local Multi-Service Compose (`docker-compose.yml`)
- Orchestrates `transaction-service` (port 8101) and `fraud-service` (port 8102) with memory/CPU limits and Docker health checks.

### 2.3 Kubernetes Resource Definitions (`k8s/base/`)
- `namespace.yaml`: Isolated `finguard` namespace.
- `configmap.yaml`: Shared microservices runtime configuration.
- `transaction-deployment.yaml` & `fraud-deployment.yaml`: Declarative deployments with non-root security context, startup, readiness, and liveness probes.
- `hpa.yaml`: Horizontal Pod Autoscalers targeting 70% CPU utilization.
- `pdb.yaml`: Pod Disruption Budgets ensuring high availability during rolling upgrades.
- `network-policy.yaml`: Restricts internal inter-pod communication.
- `ingress.yaml`: AWS Application Load Balancer (ALB) ingress routing `/transactions` and `/score`.
- `kustomization.yaml`: Kustomize base bundle.

### 2.4 Helm Production Chart (`helm/finguard/`)
- Configurable templates for deployments, services, HPA, and ALB ingress.

### 2.5 AWS EKS Infrastructure Foundation (`infrastructure/terraform/phase34/`)
- Configured specifically for **AWS Mumbai (`ap-south-1`)**.
- Dual public and private subnets, EKS Control Plane v1.29, managed node groups, VPC CNI, CoreDNS, and kube-proxy add-ons.

### 2.6 Observability (`monitoring/`)
- Prometheus scrape configuration for microservices `/metrics` endpoints.
- Grafana dashboard definition tracking RPS, latency, CPU utilization, and pod restarts.

---

## 3. Production Notice & Disclaimers
> [!NOTE]
> Local Docker and Kubernetes YAML definitions are decoupled from cloud infrastructure. Live EKS provisioning requires AWS credentials and execution of `terraform apply` in `infrastructure/terraform/phase34/` with appropriate IAM roles.

