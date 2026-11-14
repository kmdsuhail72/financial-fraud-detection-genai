"""
FinGuard AI — Enterprise Disaster Recovery & Business Continuity Service
Orchestrates RTO/RPO targets, evaluates recovery compliance, generates
failover proposals with human-approval gates, and checks multi-region health.
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional

from disaster_recovery.backup import backup_manager
from disaster_recovery.models import (
    AssessmentStatus,
    BackupManifest,
    BackupVerificationResult,
    DRHealthResponse,
    FailoverAction,
    FailoverProposal,
    RecoveryAssessment,
    RegionHealth,
    ServicePriority,
    ServiceTarget,
)


class DisasterRecoveryService:
    """Core enterprise business continuity and disaster recovery coordinator."""

    def __init__(self) -> None:
        self.backup_mgr = backup_manager
        self._targets: Dict[str, ServiceTarget] = {}
        self._active_proposal: Optional[FailoverProposal] = None
        self._init_default_targets()

    def _init_default_targets(self) -> None:
        """Configures standard RTO/RPO objectives per service tier."""
        defaults = [
            ServiceTarget(
                service_id="transaction-ingestion",
                name="Transaction Ingestion Pipeline",
                target_rto_min=30,
                target_rpo_min=5,
                priority=ServicePriority.P1,
                tier="Edge & Message Queue",
                description="Core payment and transaction ingestion via SQS/Kinesis and Kafka.",
            ),
            ServiceTarget(
                service_id="fraud-scoring",
                name="Real-Time Fraud Scoring Engine",
                target_rto_min=30,
                target_rpo_min=5,
                priority=ServicePriority.P1,
                tier="ML Inference",
                description="Real-time ML inference and risk classification microservice.",
            ),
            ServiceTarget(
                service_id="investigation-api",
                name="Analyst Investigation Case Management",
                target_rto_min=60,
                target_rpo_min=15,
                priority=ServicePriority.P2,
                tier="Operational UI & Case Store",
                description="Bedrock GenAI investigation summaries and analyst case workflow.",
            ),
            ServiceTarget(
                service_id="analytics-lake",
                name="Historical Financial Analytics Lake",
                target_rto_min=240,  # 4 hours
                target_rpo_min=60,   # 1 hour
                priority=ServicePriority.P4,
                tier="Big Data & Reporting",
                description="Analytical lakehouse, offline training partitions, and SAR reports.",
            ),
        ]
        for t in defaults:
            self._targets[t.service_id] = t

    def list_targets(self) -> List[ServiceTarget]:
        return list(self._targets.values())

    def get_target(self, service_id: str) -> Optional[ServiceTarget]:
        return self._targets.get(service_id)

    def assess_recovery(
        self,
        service_id: str,
        measured_rto_min: float,
        measured_rpo_min: float,
    ) -> Optional[RecoveryAssessment]:
        """Assesses actual recovery measurements against defined RTO/RPO targets."""
        target = self.get_target(service_id)
        if not target:
            return None

        rto_compliant = measured_rto_min <= target.target_rto_min
        rpo_compliant = measured_rpo_min <= target.target_rpo_min
        overall_compliant = rto_compliant and rpo_compliant

        gap_rto = round(max(0.0, measured_rto_min - target.target_rto_min), 2)
        gap_rpo = round(max(0.0, measured_rpo_min - target.target_rpo_min), 2)

        if overall_compliant:
            status = AssessmentStatus.COMPLIANT
        elif measured_rto_min <= target.target_rto_min * 1.25 and measured_rpo_min <= target.target_rpo_min * 1.25:
            status = AssessmentStatus.AT_RISK
        else:
            status = AssessmentStatus.BREACHED

        return RecoveryAssessment(
            service_id=target.service_id,
            name=target.name,
            target_rto_min=target.target_rto_min,
            target_rpo_min=target.target_rpo_min,
            measured_rto_min=measured_rto_min,
            measured_rpo_min=measured_rpo_min,
            rto_compliant=rto_compliant,
            rpo_compliant=rpo_compliant,
            overall_compliant=overall_compliant,
            gap_rto_min=gap_rto,
            gap_rpo_min=gap_rpo,
            status=status,
        )

    def generate_failover_plan(
        self,
        primary_healthy: bool,
        secondary_ready: bool,
        replication_lag_min: float,
        authorized_by: Optional[str] = None,
    ) -> FailoverProposal:
        """
        Decision-support workflow for multi-region failover.
        Evaluates health, secondary readiness, and replication lag against the P1 RPO (5 min).
        Requires human approval before traffic execution.
        """
        max_allowed_rpo = 5  # 5 minutes target for P1 services

        if primary_healthy:
            action = FailoverAction.STAY_PRIMARY
            approved = False
            rationale = "Primary region (Mumbai ap-south-1) is healthy and operational. No failover required."
        elif not secondary_ready:
            action = FailoverAction.BLOCKED_SECONDARY_NOT_READY
            approved = False
            rationale = "Primary region is unhealthy, but secondary region (Singapore ap-southeast-1) EKS cluster or database replica is not ready."
        elif replication_lag_min > max_allowed_rpo:
            action = FailoverAction.BLOCKED_LAG_EXCEEDED
            approved = False
            rationale = f"Replication lag is {replication_lag_min} min, which exceeds the max allowed RPO of {max_allowed_rpo} min. Data loss risk exceeds governance threshold."
        else:
            action = FailoverAction.EXECUTE_FAILOVER
            approved = True
            rationale = (
                f"Primary region is unhealthy, secondary region is confirmed ready, and replication lag "
                f"({replication_lag_min} min) is within approved RPO ({max_allowed_rpo} min). "
                f"Failover proposal generated for human operator sign-off."
            )

        proposal = FailoverProposal(
            primary_region="ap-south-1",
            secondary_region="ap-southeast-1",
            primary_healthy=primary_healthy,
            secondary_ready=secondary_ready,
            replication_lag_min=replication_lag_min,
            max_allowed_rpo_min=max_allowed_rpo,
            approved_for_failover=approved,
            recommended_action=action,
            rationale=rationale,
            human_approval_required=True,
            authorized_by=authorized_by,
        )
        self._active_proposal = proposal
        return proposal

    def verify_backup_manifest(
        self,
        manifest: BackupManifest,
        simulated_corruptions: Optional[List[str]] = None,
    ) -> BackupVerificationResult:
        """Validates backup file entries against canonical SHA-256 hashes."""
        return self.backup_mgr.verify_manifest(manifest, simulated_corruptions=simulated_corruptions)

    def get_regional_status(self) -> List[RegionHealth]:
        """Provides simulated live health of primary (Mumbai) and secondary (Singapore) regions."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return [
            RegionHealth(
                region="ap-south-1",
                role="PRIMARY",
                status="HEALTHY",
                latency_ms=18.5,
                eks_cluster_status="ACTIVE (3 AZs)",
                dynamodb_status="PITR_ENABLED (Continuous)",
                s3_crr_status="REPLICATING (Rule: CRR-To-Singapore)",
                last_checked=now_str,
            ),
            RegionHealth(
                region="ap-southeast-1",
                role="SECONDARY",
                status="HEALTHY",
                latency_ms=45.2,
                eks_cluster_status="STANDBY (Warm Spares Ready)",
                dynamodb_status="REPLICA_SYNCHRONIZED (Lag: 2.1s)",
                s3_crr_status="TARGET_BUCKET_ENCRYPTED",
                last_checked=now_str,
            ),
        ]

    def get_health(self) -> DRHealthResponse:
        """Returns the high-level health of the Disaster Recovery subsystem."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return DRHealthResponse(
            status="READY",
            primary_region="ap-south-1",
            secondary_region="ap-southeast-1",
            s3_crr_active=True,
            dynamodb_pitr_active=True,
            targets_count=len(self._targets),
            active_failover_proposal=self._active_proposal,
            timestamp=now_str,
        )


# Global singleton disaster recovery service
dr_service = DisasterRecoveryService()
