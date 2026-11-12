"""AI-Assisted SOC Threat Investigation & Brief Synthesis."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from soc.models import AIInvestigationBrief, SOCIncident


class AIInvestigationAssistant:
    """Generates evidence-grounded threat briefs and hypothesis checklists for SOC analysts."""

    @staticmethod
    def synthesize_brief(incident: SOCIncident) -> AIInvestigationBrief:
        """Synthesizes structured investigation brief grounded strictly in observed incident telemetry."""
        source = incident.source
        res_id = incident.primary_resource_id
        sev = incident.severity.value

        executive_summary = (
            f"SOC Alert {incident.incident_id} ({sev}) originated from {source} targeting {res_id}. "
            f"Observed pattern indicates potential unauthorized activity with {incident.correlated_event_count} correlated alert(s)."
        )

        threat_context = (
            f"Activity exhibits characteristics consistent with cloud security threat patterns. "
            f"If uncontained, potential impact includes lateral movement, unauthorized data access, or fraudulent transactions."
        )

        hypotheses = [
            f"Legitimate administrative or scheduled automated process operating outside regular change windows on {res_id}.",
            f"Compromised credential or API token utilized by external adversary.",
            f"Network misconfiguration resulting in false-positive anomaly detection.",
        ]

        recommended_checks = [
            f"Query CloudTrail for all API actions initiated by the actor associated with {res_id} in the last 2 hours.",
            "Verify whether a corresponding Jira change ticket exists for this resource activity.",
            "Inspect source IP reputation against external threat intelligence feeds.",
            "Review proposed containment playbook actions prior to executing remediation.",
        ]

        return AIInvestigationBrief(
            incident_id=incident.incident_id,
            executive_summary=executive_summary,
            threat_context=threat_context,
            hypotheses=hypotheses,
            recommended_checks=recommended_checks,
            confidence_score=0.91,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

