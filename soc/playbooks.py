"""SOC Response Playbooks for Threat Triage, Containment, and Remediation."""

from typing import Dict, List, Optional
from soc.models import Playbook, PlaybookAction, RemediationActionType


def get_playbook_for_incident(incident_type: str, resource_id: str) -> Playbook:
    """Selects and parameterizes an automated response playbook based on incident signature."""
    lower_type = incident_type.lower()

    if "credential" in lower_type or "iam" in lower_type or "compromise" in lower_type or "anomalous" in lower_type:
        return Playbook(
            playbook_id="PB-ACCOUNT-COMPROMISE",
            title="IAM Identity & Credential Compromise Containment",
            description="Isolate compromised IAM role/user, invalidate active STS sessions, and mandate MFA.",
            incident_type=incident_type,
            actions=[
                PlaybookAction(
                    action_id="ACT-REVOKE-STS",
                    name="Invalidate Active STS Sessions",
                    action_type=RemediationActionType.REVOKE_CREDENTIALS,
                    target_resource=resource_id,
                    parameters={"session_cutoff_hours": 1},
                    dry_run_plan=f"Attach inline deny policy AWSRevokeOlderSessions to {resource_id} with cutoff timestamp.",
                    rollback_guidance=f"Remove inline deny policy AWSRevokeOlderSessions from {resource_id}.",
                    requires_approval=True,
                ),
                PlaybookAction(
                    action_id="ACT-ENFORCE-MFA",
                    name="Enforce Immediate MFA Requirement",
                    action_type=RemediationActionType.ENFORCE_MFA,
                    target_resource=resource_id,
                    parameters={"mfa_type": "TOTP"},
                    dry_run_plan=f"Attach policy requiring aws:MultiFactorAuthPresent to all assume/invoke calls on {resource_id}.",
                    rollback_guidance=f"Detach MFA enforcement inline policy from {resource_id}.",
                    requires_approval=True,
                ),
            ],
        )

    elif "s3" in lower_type or "exfiltration" in lower_type or "malware" in lower_type or "data" in lower_type:
        return Playbook(
            playbook_id="PB-S3-DATA-PROTECTION",
            title="S3 Bucket & Object Quarantine Containment",
            description="Isolate target S3 bucket from public/cross-account access and quarantine suspicious objects.",
            incident_type=incident_type,
            actions=[
                PlaybookAction(
                    action_id="ACT-QUARANTINE-OBJECT",
                    name="Apply S3 Quarantine Tag and KMS Restrict",
                    action_type=RemediationActionType.QUARANTINE_S3_OBJECT,
                    target_resource=resource_id,
                    parameters={"quarantine_tag": "Quarantine-SecurityHold"},
                    dry_run_plan=f"Tag target object in {resource_id} with Quarantine-SecurityHold and restrict KMS decrypt policy.",
                    rollback_guidance="Remove quarantine tag and restore normal KMS access policy.",
                    requires_approval=True,
                ),
            ],
        )

    elif "fraud" in lower_type or "velocity" in lower_type or "burst" in lower_type:
        return Playbook(
            playbook_id="PB-FRAUD-BURST-CONTAINMENT",
            title="Real-Time Payment Channel Fraud Containment",
            description="Place temporary hold on suspicious bank account and throttle attack origin IP.",
            incident_type=incident_type,
            actions=[
                PlaybookAction(
                    action_id="ACT-FREEZE-CARD-CHANNEL",
                    name="Temporarily Restrict Outbound Transfers",
                    action_type=RemediationActionType.RESTRICT_USER,
                    target_resource=resource_id,
                    parameters={"hold_duration_hours": 24},
                    dry_run_plan=f"Flag account {resource_id} in core ledger with 24-hour outbound transaction review lock.",
                    rollback_guidance=f"Clear ledger review flag on account {resource_id} upon analyst verification.",
                    requires_approval=True,
                ),
            ],
        )

    else:
        # Default General Containment Playbook
        return Playbook(
            playbook_id="PB-GENERIC-CONTAINMENT",
            title="Standard SOC Threat Containment Playbook",
            description="Generic containment checklist requiring human authorization prior to remediation.",
            incident_type=incident_type,
            actions=[
                PlaybookAction(
                    action_id="ACT-BLOCK-ADVERSARY-IP",
                    name="Block Adversary Remote IP Address",
                    action_type=RemediationActionType.BLOCK_IP,
                    target_resource=resource_id,
                    parameters={"action": "DENY"},
                    dry_run_plan=f"Add adversary IP associated with {resource_id} to AWS WAF WebACL block rule.",
                    rollback_guidance="Remove adversary IP from WAF IP set.",
                    requires_approval=True,
                )
            ],
        )

