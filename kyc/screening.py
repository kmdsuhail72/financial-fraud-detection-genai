"""
FinGuard AI — Phase 25: Synthetic Screening Engine (PEP, Sanctions, Adverse Media)
Fuzzy name matching & entity resolution.
"""
import uuid
import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple
from kyc.models import ScreeningMatch, ScreeningMatchCategory, MatchConfidence

# Synthetic PEP Fixtures (Illustrative reference list for testing/dev)
SYNTHETIC_PEP_FIXTURES = [
    {
        "name": "Vladimir Volkov",
        "country": "RU",
        "position": "Former Deputy Minister of Energy",
        "source": "PEP-GLOBAL-SYNTHETIC-001",
        "notes": "PEP Tier 1: Senior government executive"
    },
    {
        "name": "Elena Rostova",
        "country": "CY",
        "position": "Immediate family member of PEP (Spouse of Regional Governor)",
        "source": "PEP-GLOBAL-SYNTHETIC-002",
        "notes": "PEP Tier 2: Close associate/family member"
    },
    {
        "name": "Arthur Pendelton",
        "country": "GB",
        "position": "Member of Parliament / Defense Committee",
        "source": "PEP-GLOBAL-SYNTHETIC-003",
        "notes": "PEP Tier 1: Legislative official"
    },
    {
        "name": "Senator James Vance",
        "country": "US",
        "position": "Senior Committee Member",
        "source": "PEP-GLOBAL-SYNTHETIC-004",
        "notes": "PEP Tier 1: Federal lawmaker"
    },
    {
        "name": "Chen Wei",
        "country": "CN",
        "position": "Director of State Owned Enterprise",
        "source": "PEP-GLOBAL-SYNTHETIC-005",
        "notes": "PEP Tier 2: State enterprise leadership"
    }
]

# Synthetic Sanctions Fixtures (Illustrative reference list)
SYNTHETIC_SANCTIONS_FIXTURES = [
    {
        "name": "Al-Farooq Logistics",
        "country": "AE",
        "program": "GLOBAL-ILLICIT-LOGISTICS",
        "source": "SANCTION-SYNTHETIC-001",
        "notes": "Designated for facilitating prohibited maritime transport"
    },
    {
        "name": "Red Star Maritime Ltd",
        "country": "RU",
        "program": "MARITIME-RESTRICTION-LIST",
        "source": "SANCTION-SYNTHETIC-002",
        "notes": "Designated for evading oil price cap mechanisms"
    },
    {
        "name": "Dmitry Belov",
        "country": "RU",
        "program": "SPECIAL-DESIGNATED-SYNTHETIC",
        "source": "SANCTION-SYNTHETIC-003",
        "notes": "Individual designated for procurement of dual-use technologies"
    },
    {
        "name": "Phoenix Shadow Corp",
        "country": "PA",
        "program": "ANTI-PROLIFERATION-SYNTHETIC",
        "source": "SANCTION-SYNTHETIC-004",
        "notes": "Shell corporation used in multi-jurisdictional layering"
    },
    {
        "name": "Northern Front Holdings",
        "country": "SG",
        "program": "FINANCIAL-RESTRICTIONS-SYNTHETIC",
        "source": "SANCTION-SYNTHETIC-005",
        "notes": "Financial intermediary subject to asset freeze protocols"
    }
]

# Synthetic Adverse Media Fixtures (Illustrative reference list)
SYNTHETIC_ADVERSE_MEDIA_FIXTURES = [
    {
        "name": "Carlos Mendez",
        "country": "MX",
        "headline": "Investigation opened into cross-border real estate money laundering scheme",
        "source": "MEDIA-SYNTHETIC-001",
        "publisher": "Financial Times Synthetic Wire"
    },
    {
        "name": "Apex Global Trading",
        "country": "HK",
        "headline": "Customs agency probes shell entities for invoice misdirection and tax fraud",
        "source": "MEDIA-SYNTHETIC-002",
        "publisher": "Global Crime Monitor"
    },
    {
        "name": "Victor Vance",
        "country": "US",
        "headline": "Former executive charged in synthetic securities manipulation and wire fraud",
        "source": "MEDIA-SYNTHETIC-003",
        "publisher": "Regulatory Enforcement Dispatch"
    }
]


def normalize_string(val: str) -> str:
    """Strip punctuation and normalize whitespace for robust fuzzy matching."""
    if not val:
        return ""
    clean = re.sub(r"[^\w\s]", " ", val.lower())
    return " ".join(clean.split())


def compute_fuzzy_similarity(s1: str, s2: str) -> float:
    """
    Computes a hybrid token-sort and sequence similarity score [0.0, 1.0].
    Handles reordered words, titles, and partial tokens cleanly.
    """
    n1 = normalize_string(s1)
    n2 = normalize_string(s2)
    
    if not n1 or not n2:
        return 0.0
    
    if n1 == n2:
        return 1.0

    # Direct Sequence Match
    direct_ratio = SequenceMatcher(None, n1, n2).ratio()
    
    # Token-sort comparison
    tokens1 = sorted(n1.split())
    tokens2 = sorted(n2.split())
    sorted_str1 = " ".join(tokens1)
    sorted_str2 = " ".join(tokens2)
    sorted_ratio = SequenceMatcher(None, sorted_str1, sorted_str2).ratio()
    
    # Check token overlap (Jaccard-like bonus)
    set1, set2 = set(tokens1), set(tokens2)
    overlap = len(set1.intersection(set2)) / max(len(set1), len(set2))
    
    # Return best composite match
    return round(max(direct_ratio, sorted_ratio, overlap), 3)


def map_score_to_confidence(score: float) -> MatchConfidence:
    if score >= 0.95:
        return MatchConfidence.EXACT
    elif score >= 0.85:
        return MatchConfidence.HIGH
    elif score >= 0.70:
        return MatchConfidence.MEDIUM
    return MatchConfidence.LOW


class ScreeningEngine:
    """
    Synthetic multi-category screening engine for Onboarding and CDD.
    Matches entity against PEP, Sanctions, and Adverse Media fixtures.
    """

    def __init__(self, match_threshold: float = 0.70):
        self.match_threshold = match_threshold

    def screen(self, full_name: str, country: Optional[str] = None) -> List[ScreeningMatch]:
        matches: List[ScreeningMatch] = []
        
        # 1. PEP Screening
        for pep in SYNTHETIC_PEP_FIXTURES:
            score = compute_fuzzy_similarity(full_name, pep["name"])
            if score >= self.match_threshold:
                conf = map_score_to_confidence(score)
                matches.append(
                    ScreeningMatch(
                        match_id=f"PEP-MATCH-{uuid.uuid4().hex[:8].upper()}",
                        category=ScreeningMatchCategory.PEP,
                        matched_entity_name=pep["name"],
                        entity_country=pep["country"],
                        similarity_score=score,
                        match_confidence=conf,
                        source_reference=pep["source"],
                        snippet_or_reason=f"PEP Hit: {pep['position']}. {pep['notes']}"
                    )
                )

        # 2. Sanctions Screening
        for sanction in SYNTHETIC_SANCTIONS_FIXTURES:
            score = compute_fuzzy_similarity(full_name, sanction["name"])
            if score >= self.match_threshold:
                conf = map_score_to_confidence(score)
                matches.append(
                    ScreeningMatch(
                        match_id=f"SANCTION-MATCH-{uuid.uuid4().hex[:8].upper()}",
                        category=ScreeningMatchCategory.SANCTIONS,
                        matched_entity_name=sanction["name"],
                        entity_country=sanction["country"],
                        similarity_score=score,
                        match_confidence=conf,
                        source_reference=sanction["source"],
                        snippet_or_reason=f"Sanctions Hit ({sanction['program']}): {sanction['notes']}"
                    )
                )

        # 3. Adverse Media Screening
        for media in SYNTHETIC_ADVERSE_MEDIA_FIXTURES:
            score = compute_fuzzy_similarity(full_name, media["name"])
            if score >= self.match_threshold:
                conf = map_score_to_confidence(score)
                matches.append(
                    ScreeningMatch(
                        match_id=f"MEDIA-MATCH-{uuid.uuid4().hex[:8].upper()}",
                        category=ScreeningMatchCategory.ADVERSE_MEDIA,
                        matched_entity_name=media["name"],
                        entity_country=media["country"],
                        similarity_score=score,
                        match_confidence=conf,
                        source_reference=media["source"],
                        snippet_or_reason=f"Adverse Media: '{media['headline']}' ({media['publisher']})"
                    )
                )

        # Sort matches by highest similarity score
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches
