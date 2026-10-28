"""Signal-based calibrated evidence strength evaluation and qualitative component assessment."""

import logging
from typing import List, Tuple, Optional
from researchmind.schemas.models import (
    RetrievalCandidate,
    EvidenceStrength,
    ComponentQualityAssessment,
)
from researchmind.config import settings

logger = logging.getLogger(__name__)


def evaluate_component_quality(
    candidates: List[RetrievalCandidate],
    query: str,
    target_paper_id: Optional[str] = None,
    provider_status: str = "api_success",
    grounding_supported: int = 0,
    grounding_total: int = 0,
) -> ComponentQualityAssessment:
    """Qualitatively assess key operational components to avoid unjustified 'Strong' labels."""
    from researchmind.retrieval.prioritization import is_methodology_query, DEFAULT_METHODOLOGY_TERMS

    # 1. Gemini availability
    if "fallback" in provider_status or "unavailable" in provider_status:
        gemini_avail = "Failed temporarily; fallback activated"
    elif provider_status == "offline_fallback":
        gemini_avail = "Offline fallback active"
    else:
        gemini_avail = "Available (API Success)"

    # 2. Citation generation
    if len(candidates) > 0:
        citation_gen = "Functioning"
    else:
        citation_gen = "No citations generated"

    # 3. Target-paper relevance
    if target_paper_id:
        if all(c.paper_id == target_paper_id for c in candidates):
            target_rel = "Verified"
        elif any(c.paper_id == target_paper_id for c in candidates):
            target_rel = "Needs verification"
        else:
            target_rel = "Mismatched"
    else:
        target_rel = "General / Multi-paper"

    # 4. Methodology extraction
    if is_methodology_query(query):
        method_chunks = [
            c for c in candidates
            if any(m in f"{c.section or ''} {c.subsection or ''}".lower() for m in DEFAULT_METHODOLOGY_TERMS)
            or any(m in c.text[:300].lower() for m in DEFAULT_METHODOLOGY_TERMS)
        ]
        # Check if non-metadata methodology chunks exist
        valid_method_chunks = [
            c for c in method_chunks
            if "introduction / header" not in (c.section or "").lower()
        ]

        if len(valid_method_chunks) >= 2:
            method_ext = "Sufficient"
        elif len(valid_method_chunks) >= 1:
            method_ext = "Partial"
        else:
            method_ext = "Insufficient"
    else:
        method_ext = "N/A"

    # 5. Cross-paper contamination
    if target_paper_id:
        c_papers = set(c.paper_id for c in candidates)
        if len(c_papers) <= 1 and (not c_papers or list(c_papers)[0] == target_paper_id):
            cross_contam = "None detected"
        else:
            cross_contam = "Present or possible"
    else:
        cross_contam = "None detected (Multi-paper query)"

    # 6. Overall answer quality
    if (
        method_ext == "Insufficient"
        or cross_contam == "Present or possible"
        or (grounding_total > 0 and grounding_supported / grounding_total < 0.5)
    ):
        overall_qual = "Needs improvement"
    elif method_ext == "Partial" or gemini_avail != "Available (API Success)":
        overall_qual = "Moderate"
    else:
        overall_qual = "High"

    return ComponentQualityAssessment(
        gemini_availability=gemini_avail,
        citation_generation=citation_gen,
        target_paper_relevance=target_rel,
        methodology_extraction=method_ext,
        cross_paper_contamination=cross_contam,
        overall_answer_quality=overall_qual,
    )


def calculate_evidence_strength(
    candidates: List[RetrievalCandidate],
    min_score_threshold: Optional[float] = None,
    component_assessment: Optional[ComponentQualityAssessment] = None,
) -> Tuple[EvidenceStrength, str]:
    """Determine calibrated evidence strength combining retrieval signals and component quality.
    
    Args:
        candidates: List of top retrieved / reranked candidates.
        min_score_threshold: Minimum score to consider a chunk valid evidence.
        component_assessment: Optional qualitative evaluation of system components.
        
    Returns:
        Tuple of (EvidenceStrength enum, explanation rationale).
    """
    threshold = min_score_threshold if min_score_threshold is not None else settings.MIN_EVIDENCE_SCORE

    if not candidates:
        return (
            EvidenceStrength.INSUFFICIENT,
            "No supporting research documents were retrieved for this query.",
        )

    # Inspect top candidate score
    top_cand = candidates[0]
    top_score = top_cand.reranker_score if top_cand.reranker_score is not None else (
        top_cand.dense_score if top_cand.dense_score is not None else top_cand.final_score
    )

    if top_score < threshold:
        return (
            EvidenceStrength.INSUFFICIENT,
            f"Retrieved passages have low relevance confidence (top score: {top_score:.3f} < {threshold:.2f}).",
        )

    # Multi-source agreement, cross-retrieval consensus, and candidate distribution
    unique_papers = len(set(c.paper_id for c in candidates))
    dual_consensus_count = sum(1 for c in candidates if c.dense_rank is not None and c.bm25_rank is not None)
    high_score_count = sum(1 for c in candidates if (c.reranker_score or c.dense_score or 0) >= 0.70)

    base_strength = EvidenceStrength.WEAK
    base_rationale = f"Weak evidence with limited retrieval confidence (top score: {top_score:.3f}). Claims should be treated with caution."

    if (top_score >= 0.75 and high_score_count >= 2) or (dual_consensus_count >= 2 and top_score >= 0.65):
        base_strength = EvidenceStrength.STRONG
        base_rationale = (
            f"Strong evidence supported by {len(candidates)} high-confidence passages across {unique_papers} papers "
            f"with dual retrieval consensus (top score: {top_score:.3f})."
        )
    elif top_score >= 0.50 or high_score_count >= 1:
        base_strength = EvidenceStrength.MODERATE
        base_rationale = f"Moderate evidence found in {len(candidates)} passages across {unique_papers} papers (top score: {top_score:.3f})."

    # Calibration adjustment based on Component Quality Assessment (Requirement E)
    if component_assessment:
        if component_assessment.overall_answer_quality == "Needs improvement":
            if base_strength == EvidenceStrength.STRONG:
                return (
                    EvidenceStrength.MODERATE,
                    f"Calibrated from Strong to Moderate: {component_assessment.overall_answer_quality} "
                    f"(Methodology extraction: {component_assessment.methodology_extraction}; "
                    f"Cross-paper contamination: {component_assessment.cross_paper_contamination}).",
                )
        elif component_assessment.methodology_extraction == "Insufficient":
            if base_strength == EvidenceStrength.STRONG:
                return (
                    EvidenceStrength.MODERATE,
                    "Calibrated from Strong to Moderate: Methodology extraction is insufficient from retrieved passages.",
                )

    return base_strength, base_rationale
