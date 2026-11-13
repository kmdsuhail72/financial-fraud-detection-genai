"""
FinGuard AI — Phase 26: Explainable Field Consistency Verification Engine
Compares OCR/extracted document attributes against customer profile data.
"""
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple
from document_verification.models import (
    FieldConsistencyCheck,
    FieldConsistencyReport,
    ConsistencyVerdict,
)


def normalize_val(val: str) -> str:
    """Normalizes string for comparison by removing punctuation and whitespace."""
    if not val:
        return ""
    clean = re.sub(r"[^\w\s]", "", val.lower())
    return " ".join(clean.split())


def compute_string_similarity(s1: str, s2: str) -> float:
    """Computes hybrid token-sort and sequence similarity between two field values."""
    n1 = normalize_val(s1)
    n2 = normalize_val(s2)
    
    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    
    seq_ratio = SequenceMatcher(None, n1, n2).ratio()
    tokens1 = sorted(n1.split())
    tokens2 = sorted(n2.split())
    token_ratio = SequenceMatcher(None, " ".join(tokens1), " ".join(tokens2)).ratio()
    
    return round(max(seq_ratio, token_ratio), 3)


class FieldConsistencyEngine:
    """
    Evaluates field-level congruence between document metadata and customer profile records.
    """

    @staticmethod
    def evaluate_consistency(
        extracted_fields: Dict[str, str],
        expected_profile: Dict[str, str]
    ) -> FieldConsistencyReport:
        checks: List[FieldConsistencyCheck] = []
        scores: List[float] = []
        mismatch_count = 0

        # Common target fields to check if present
        all_keys = set(extracted_fields.keys()).union(set(expected_profile.keys()))
        
        if not all_keys:
            return FieldConsistencyReport(
                checks=[],
                overall_consistency_score=1.0,
                is_consistent=True,
                mismatch_count=0,
                notes="No fields provided for comparison."
            )

        for key in sorted(all_keys):
            doc_val = extracted_fields.get(key, "").strip()
            exp_val = expected_profile.get(key, "").strip()

            if not doc_val or not exp_val:
                verdict = ConsistencyVerdict.NOT_APPLICABLE
                score = 0.5
                explanation = f"Field '{key}' missing from one side of comparison (Doc: '{doc_val}', Expected: '{exp_val}')."
            else:
                sim = compute_string_similarity(doc_val, exp_val)
                scores.append(sim)

                if sim >= 0.95:
                    verdict = ConsistencyVerdict.MATCH
                    explanation = f"Exact or near-exact match on '{key}' ({int(sim*100)}% congruence)."
                elif sim >= 0.70:
                    verdict = ConsistencyVerdict.PARTIAL_MATCH
                    explanation = f"Partial match on '{key}' ({int(sim*100)}% similarity) due to formatting or minor token reordering."
                else:
                    verdict = ConsistencyVerdict.MISMATCH
                    mismatch_count += 1
                    explanation = f"CRITICAL MISMATCH on '{key}': Doc='{doc_val}' vs Expected='{exp_val}' ({int(sim*100)}% similarity)."

                checks.append(
                    FieldConsistencyCheck(
                        field_name=key,
                        customer_value=exp_val,
                        document_value=doc_val,
                        similarity_score=sim,
                        verdict=verdict,
                        explanation=explanation
                    )
                )

        overall_score = round(sum(scores) / max(len(scores), 1), 3) if scores else 0.5
        is_consistent = mismatch_count == 0 and overall_score >= 0.75

        if is_consistent:
            notes = f"All {len(checks)} verified fields exhibit acceptable consistency (Score: {overall_score*100:.1f}%)."
        else:
            notes = f"Detected {mismatch_count} field discrepancies. Document requires manual analyst reconciliation."

        return FieldConsistencyReport(
            checks=checks,
            overall_consistency_score=overall_score,
            is_consistent=is_consistent,
            mismatch_count=mismatch_count,
            notes=notes
        )

