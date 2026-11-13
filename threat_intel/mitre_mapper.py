"""MITRE ATT&CK Framework Mapping Engine for Financial Crime & Cyber Threat Intelligence."""

from __future__ import annotations

from typing import Dict, List, Optional
from threat_intel.models import MITRETechnique, MITRETactic

# Comprehensive catalog of relevant Enterprise ATT&CK techniques
MITRE_CATALOG: Dict[str, MITRETechnique] = {
    "T1078": MITRETechnique(
        technique_id="T1078",
        name="Valid Accounts",
        tactic=MITRETactic.INITIAL_ACCESS.value,
        description="Adversaries obtain and abuse credentials of existing accounts to bypass defenses and access banking portals.",
        url="https://attack.mitre.org/techniques/T1078/",
    ),
    "T1110": MITRETechnique(
        technique_id="T1110",
        name="Brute Force",
        tactic=MITRETactic.CREDENTIAL_ACCESS.value,
        description="Adversaries systematically guess passwords or credential stuff against banking login endpoints.",
        url="https://attack.mitre.org/techniques/T1110/",
    ),
    "T1071": MITRETechnique(
        technique_id="T1071",
        name="Application Layer Protocol",
        tactic=MITRETactic.COMMAND_AND_CONTROL.value,
        description="Adversaries communicate with malware or compromised devices using HTTP/HTTPS or DNS protocols.",
        url="https://attack.mitre.org/techniques/T1071/",
    ),
    "T1566": MITRETechnique(
        technique_id="T1566",
        name="Phishing",
        tactic=MITRETactic.INITIAL_ACCESS.value,
        description="Adversaries send deceptive messages or credential-harvesting landing pages to trick customers into revealing credentials.",
        url="https://attack.mitre.org/techniques/T1566/",
    ),
    "T1090": MITRETechnique(
        technique_id="T1090",
        name="Proxy",
        tactic=MITRETactic.COMMAND_AND_CONTROL.value,
        description="Adversaries route illicit traffic through open proxies, Tor exit nodes, or VPNs to mask origin.",
        url="https://attack.mitre.org/techniques/T1090/",
    ),
    "T1567": MITRETechnique(
        technique_id="T1567",
        name="Exfiltration Over Web Service",
        tactic=MITRETactic.EXFILTRATION.value,
        description="Adversaries exfiltrate stolen banking data or customer records to cloud storage or paste sites.",
        url="https://attack.mitre.org/techniques/T1567/",
    ),
    "T1589": MITRETechnique(
        technique_id="T1589",
        name="Gather Victim Identity Information",
        tactic=MITRETactic.INITIAL_ACCESS.value,
        description="Adversaries collect PII, phone numbers, or account details to assemble synthetic identities.",
        url="https://attack.mitre.org/techniques/T1589/",
    ),
    "T1539": MITRETechnique(
        technique_id="T1539",
        name="Steal Web Session Cookie",
        tactic=MITRETactic.CREDENTIAL_ACCESS.value,
        description="Adversaries capture session cookies or tokens to bypass multi-factor authentication (MFA).",
        url="https://attack.mitre.org/techniques/T1539/",
    ),
    "T1059": MITRETechnique(
        technique_id="T1059",
        name="Command and Scripting Interpreter",
        tactic=MITRETactic.EXECUTION.value,
        description="Adversaries execute commands via shells, Python, or PowerShell on compromised endpoints.",
        url="https://attack.mitre.org/techniques/T1059/",
    ),
    "T1486": MITRETechnique(
        technique_id="T1486",
        name="Data Encrypted for Impact",
        tactic=MITRETactic.IMPACT.value,
        description="Ransomware encrypts critical databases or file systems to disrupt operations and extort funds.",
        url="https://attack.mitre.org/techniques/T1486/",
    ),
}

# Mapping from common threat tags/categories to ATT&CK techniques
THREAT_CATEGORY_TO_MITRE: Dict[str, List[str]] = {
    "c2": ["T1071", "T1090"],
    "command_and_control": ["T1071", "T1090"],
    "phishing": ["T1566"],
    "credential_theft": ["T1110", "T1539", "T1078"],
    "credential_stuffing": ["T1110", "T1078"],
    "proxy": ["T1090"],
    "vpn": ["T1090"],
    "tor": ["T1090"],
    "exfiltration": ["T1567"],
    "synthetic_identity": ["T1589", "T1078"],
    "ransomware": ["T1486", "T1059"],
    "botnet": ["T1071", "T1090"],
    "account_takeover": ["T1078", "T1539"],
}


class MITREMapper:
    """Provides MITRE ATT&CK correlation, lookup, and taxonomy services."""

    @classmethod
    def get_technique(cls, technique_id: str) -> Optional[MITRETechnique]:
        """Returns technique metadata by ATT&CK ID."""
        return MITRE_CATALOG.get(technique_id.upper())

    @classmethod
    def map_threat_types_to_techniques(cls, threat_types: List[str]) -> List[MITRETechnique]:
        """Resolves threat type categories to associated MITRE techniques."""
        technique_ids = set()
        for t in threat_types:
            clean = t.lower().replace("-", "_").replace(" ", "_")
            if clean in THREAT_CATEGORY_TO_MITRE:
                technique_ids.update(THREAT_CATEGORY_TO_MITRE[clean])

        result: List[MITRETechnique] = []
        for tid in sorted(technique_ids):
            tech = MITRE_CATALOG.get(tid)
            if tech:
                result.append(tech)
        return result

    @classmethod
    def list_all_techniques(cls) -> List[MITRETechnique]:
        """Returns the complete registered catalog of MITRE techniques."""
        return list(MITRE_CATALOG.values())
