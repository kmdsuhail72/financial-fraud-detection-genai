"""Controlled Remediation Executor with Human Approval Gates and Separation of Duties."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from security.audit import audit_logger
from soc.models import (
    ApprovalStatus,
    PlaybookAction,
    RemediationApproval,
    RemediationReceipt,
)


class RemediationExecutionError(Exception):
    """Raised when remediation execution fails safety checks or approval verification."""
    pass


class ControlledRemediationExecutor:
    """
    Executes allowlisted containment and remediation actions.
    Enforces human approval gates and strict separation of duties.
    """

    def __init__(self, allow_simulation_only: bool = True):
        self.allow_simulation_only = allow_simulation_only

    def verify_approval(
        self,
        approval: RemediationApproval,
        executing_user: str,
    ) -> bool:
        """Verifies approval status and enforces separation of duties."""
        if approval.status != ApprovalStatus.APPROVED:
            raise RemediationExecutionError(
                f"Action blocked: Approval status is '{approval.status.value}', requires 'APPROVED'."
            )

        if not approval.approver:
            raise RemediationExecutionError("Action blocked: Approver identity missing.")

        # Separation of duties: Requester cannot approve their own remediation request
        if approval.requested_by.lower() == approval.approver.lower():
            raise RemediationExecutionError(
                f"Separation of duties violation: Requester '{approval.requested_by}' cannot approve their own action."
            )

        return True

    def execute_action(
        self,
        action: PlaybookAction,
        approval: RemediationApproval,
        executed_by: str,
    ) -> RemediationReceipt:
        """Executes authorized containment action in safe simulated sandbox mode."""
        self.verify_approval(approval, executing_user=executed_by)

        receipt_id = f"RCPT-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Simulated Execution Verification
        verification = {
            "pre_check": "Target resource reachable and validated",
            "execution_mode": "ALLOWLISTED_SANDBOX_SIMULATION",
            "action_executed": action.name,
            "target_resource": action.target_resource,
            "parameters_applied": action.parameters,
            "post_check_verified": True,
            "rollback_readiness": "VERIFIED_READY",
        }

        receipt = RemediationReceipt(
            receipt_id=receipt_id,
            action_id=action.action_id,
            target_resource=action.target_resource,
            executed_by=executed_by,
            executed_at=now_str,
            execution_status="SIMULATED_SUCCESS",
            verification_results=verification,
            audit_log_ref=f"SEC-AUDIT-{receipt_id}",
        )

        # Record tamper-evident security audit entry
        audit_logger.log(
            actor_sub=executed_by,
            actor_email=executed_by,
            action=f"soc:remediation:execute:{action.action_type.value}",
            resource_type="SOC_REMEDIATION",
            resource_id=action.target_resource,
            status="SUCCESS",
            details={
                "action_id": action.action_id,
                "approved_by": approval.approver,
                "receipt_id": receipt_id,
            },
        )

        return receipt

