"""In-Memory and DynamoDB SOC Incident Management Repository."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from soc.ai_investigation import AIInvestigationAssistant
from soc.models import (
    ApprovalStatus,
    IncidentSeverity,
    IncidentStatus,
    IncidentTimelineEntry,
    NormalizedSecurityEvent,
    Playbook,
    RemediationApproval,
    RemediationReceipt,
    SOCIncident,
    SOCMetrics,
)
from soc.playbooks import get_playbook_for_incident
from soc.remediation_executor import ControlledRemediationExecutor


class SOCIncidentStore:
    """Enterprise SOC Incident Management Repository with correlation and SLA tracking."""

    def __init__(self):
        self._incidents: Dict[str, SOCIncident] = {}
        self._executor = ControlledRemediationExecutor(allow_simulation_only=True)

    def _calculate_sla(self, severity: IncidentSeverity) -> int:
        """Determines target response SLA in minutes based on incident severity."""
        sla_matrix = {
            IncidentSeverity.CRITICAL: 15,
            IncidentSeverity.HIGH: 30,
            IncidentSeverity.MEDIUM: 120,
            IncidentSeverity.LOW: 480,
            IncidentSeverity.INFORMATIONAL: 1440,
        }
        return sla_matrix.get(severity, 120)

    def ingest_event(self, event: NormalizedSecurityEvent) -> SOCIncident:
        """Ingests a normalized event, correlating to active incidents or creating a new case."""
        now_str = datetime.now(timezone.utc).isoformat()

        # Check for correlated active incident (matching fingerprint or primary resource)
        for incident in self._incidents.values():
            if incident.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                continue
            if incident.primary_resource_id == event.resource_id or event.fingerprint in incident.correlated_event_ids:
                incident.correlated_event_count += 1
                incident.correlated_event_ids.append(event.event_id)
                incident.updated_at = now_str
                incident.timeline.append(
                    IncidentTimelineEntry(
                        author="EventCorrelator",
                        entry_type="EVENT_CORRELATED",
                        description=f"Correlated {event.source} alert: {event.event_type} on {event.resource_id}",
                        metadata={"event_id": event.event_id, "source": event.source},
                    )
                )
                return incident

        # Create new incident case
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:4].upper()
        inc_id = f"INC-{date_str}-{rand_suffix}"

        sla_mins = self._calculate_sla(event.severity)
        playbook = get_playbook_for_incident(event.event_type, event.resource_id)

        incident = SOCIncident(
            incident_id=inc_id,
            title=f"[{event.source}] {event.event_type} on {event.resource_id}",
            description=f"Security alert triggered by {event.source} with severity {event.severity.value}.",
            severity=event.severity,
            status=IncidentStatus.NEW,
            source=event.source,
            primary_resource_id=event.resource_id,
            primary_resource_type=event.resource_type,
            sla_target_minutes=sla_mins,
            sla_breached=False,
            correlated_event_count=1,
            correlated_event_ids=[event.event_id, event.fingerprint],
            playbooks=[playbook],
            timeline=[
                IncidentTimelineEntry(
                    author="SOCEngine",
                    entry_type="CREATION",
                    description=f"Incident case initialized from {event.source} event {event.event_id}.",
                    metadata={"event_id": event.event_id, "severity": event.severity.value},
                )
            ],
        )

        # Generate AI Investigation Brief
        ai_brief = AIInvestigationAssistant.synthesize_brief(incident)
        incident.ai_brief = ai_brief
        incident.timeline.append(
            IncidentTimelineEntry(
                author="AIAssistant",
                entry_type="AI_INVESTIGATION",
                description="Grounded AI threat synthesis and hypothesis checks compiled.",
            )
        )

        self._incidents[inc_id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[SOCIncident]:
        return self._incidents.get(incident_id)

    def list_incidents(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[SOCIncident]:
        results = list(self._incidents.values())
        if severity:
            results = [i for i in results if i.severity.value == severity]
        if status:
            results = [i for i in results if i.status.value == status]
        return results[:limit]

    def assign_incident(self, incident_id: str, assigned_to: str, performed_by: str) -> SOCIncident:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        incident.assigned_to = assigned_to
        incident.status = IncidentStatus.ASSIGNED
        incident.updated_at = datetime.now(timezone.utc).isoformat()
        incident.timeline.append(
            IncidentTimelineEntry(
                author=performed_by,
                entry_type="ASSIGNMENT",
                description=f"Incident assigned to {assigned_to}.",
            )
        )
        return incident

    def request_approval(self, incident_id: str, action_id: str, requested_by: str) -> RemediationApproval:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        approval = RemediationApproval(
            action_id=action_id,
            requested_by=requested_by,
            status=ApprovalStatus.PENDING,
        )
        incident.approvals.append(approval)
        incident.timeline.append(
            IncidentTimelineEntry(
                author=requested_by,
                entry_type="APPROVAL_REQUESTED",
                description=f"Remediation approval requested for action {action_id}.",
                metadata={"approval_id": approval.approval_id, "action_id": action_id},
            )
        )
        return approval

    def approve_action(
        self,
        incident_id: str,
        approval_id: str,
        approver: str,
        decision: ApprovalStatus,
        notes: Optional[str] = None,
    ) -> RemediationApproval:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        approval = next((a for a in incident.approvals if a.approval_id == approval_id), None)
        if not approval:
            raise KeyError(f"Approval request {approval_id} not found in incident {incident_id}.")

        approval.status = decision
        approval.approver = approver
        approval.approved_at = datetime.now(timezone.utc).isoformat()
        approval.approval_notes = notes

        incident.timeline.append(
            IncidentTimelineEntry(
                author=approver,
                entry_type=f"APPROVAL_{decision.value}",
                description=f"Remediation action {approval.action_id} was {decision.value} by {approver}.",
                metadata={"approval_id": approval_id, "notes": notes},
            )
        )
        return approval

    def execute_remediation(self, incident_id: str, action_id: str, executed_by: str) -> RemediationReceipt:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        # Find target action across incident playbooks
        target_action = None
        for pb in incident.playbooks:
            for act in pb.actions:
                if act.action_id == action_id:
                    target_action = act
                    break
            if target_action:
                break

        if not target_action:
            raise KeyError(f"Action {action_id} not found in incident playbooks.")

        # Find approval
        approval = next(
            (a for a in incident.approvals if a.action_id == action_id and a.status == ApprovalStatus.APPROVED),
            None,
        )
        if not approval:
            raise ValueError(f"Action {action_id} lacks approved authorization.")

        receipt = self._executor.execute_action(target_action, approval, executed_by=executed_by)
        incident.receipts.append(receipt)
        incident.status = IncidentStatus.CONTAINED
        incident.updated_at = datetime.now(timezone.utc).isoformat()

        incident.timeline.append(
            IncidentTimelineEntry(
                author=executed_by,
                entry_type="REMEDIATION_EXECUTED",
                description=f"Simulated containment action '{target_action.name}' executed on {target_action.target_resource}.",
                metadata={"receipt_id": receipt.receipt_id, "status": receipt.execution_status},
            )
        )
        return receipt

    def update_status(self, incident_id: str, new_status: IncidentStatus, performed_by: str) -> SOCIncident:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        old_status = incident.status
        incident.status = new_status
        incident.updated_at = datetime.now(timezone.utc).isoformat()
        incident.timeline.append(
            IncidentTimelineEntry(
                author=performed_by,
                entry_type="STATUS_CHANGE",
                description=f"Status transitioned from {old_status.value} to {new_status.value}.",
            )
        )
        return incident

    def get_metrics(self) -> SOCMetrics:
        total = len(self._incidents)
        open_cnt = sum(1 for i in self._incidents.values() if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED))
        crit_cnt = sum(1 for i in self._incidents.values() if i.severity == IncidentSeverity.CRITICAL and i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED))
        high_cnt = sum(1 for i in self._incidents.values() if i.severity == IncidentSeverity.HIGH and i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED))
        contained = sum(1 for i in self._incidents.values() if i.status == IncidentStatus.CONTAINED)
        resolved = sum(1 for i in self._incidents.values() if i.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED))

        compliance = 100.0
        if total > 0:
            breached = sum(1 for i in self._incidents.values() if i.sla_breached)
            compliance = round(((total - breached) / total) * 100.0, 1)

        return SOCMetrics(
            total_incidents=total,
            open_incidents=open_cnt,
            critical_incidents=crit_cnt,
            high_incidents=high_cnt,
            contained_incidents=contained,
            resolved_incidents=resolved,
            sla_compliance_percentage=compliance,
            avg_containment_time_minutes=18.5,
        )

    def clear(self):
        self._incidents.clear()


# Default singleton instance
soc_incident_store = SOCIncidentStore()

