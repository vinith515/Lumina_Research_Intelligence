"""Section and content prioritization boosting for methodology and technical extraction."""

import logging
import re
from typing import List, Optional
from researchmind.schemas.models import RetrievalCandidate

logger = logging.getLogger(__name__)

DEFAULT_METHODOLOGY_TERMS = [
    "methodology",
    "methods",
    "materials and methods",
    "proposed approach",
    "proposed method",
    "framework",
    "workflow",
    "spatial feature engineering",
    "feature engineering",
    "quality validation",
    "quality control",
    "experiments",
    "architecture",
    "pipeline",
    "implementation",
]

METADATA_HEADER_TERMS = [
    "introduction / header",
    "title",
    "ethics statement",
    "author",
    "affiliation",
    "acknowledgments",
]


def is_methodology_query(query: str) -> bool:
    """Detect if query is asking for methodology, workflow, techniques, or how an approach works."""
    q_lower = query.lower()
    triggers = [
        "technique",
        "method",
        "methodology",
        "how does",
        "how do",
        "proposed approach",
        "approach",
        "workflow",
        "framework",
        "architecture",
        "pipeline",
        "procedure",
        "algorithm",
        "feature engineering",
        "validation",
        "extraction",
        "work?",
        "works?",
    ]
    return any(t in q_lower for t in triggers)


def score_candidate_priority(
    candidate: RetrievalCandidate,
    is_methodology: bool = True,
    methodology_terms: Optional[List[str]] = None,
) -> float:
    """Compute priority weight multiplier for a candidate chunk."""
    if not is_methodology:
        return 1.0

    terms = methodology_terms or DEFAULT_METHODOLOGY_TERMS
    section_text = f"{candidate.section or ''} {candidate.subsection or ''}".lower()
    content_head = candidate.text[:300].lower()

    # Check for metadata/header chunks that lack methodology content
    is_metadata_section = any(meta in section_text for meta in METADATA_HEADER_TERMS)
    has_method_in_section = any(term in section_text for term in terms)
    has_method_in_text = any(term in content_head for term in terms)

    if has_method_in_section:
        # Strong boost for explicit methodology sections (e.g. "2 Materials and Methods", "2.4 Feature Engineering")
        return 1.40
    elif has_method_in_text and not is_metadata_section:
        # Moderate boost for methodology content in non-header section
        return 1.20
    elif is_metadata_section and not has_method_in_text:
        # Significant penalty for purely bibliographic/author headers
        return 0.50

    return 1.0


def prioritize_candidates(
    candidates: List[RetrievalCandidate],
    query: str,
    methodology_terms: Optional[List[str]] = None,
    top_k: Optional[int] = None,
) -> List[RetrievalCandidate]:
    """Reorder and boost candidates prioritizing methodology sections when applicable."""
    if not candidates:
        return []

    is_method = is_methodology_query(query)
    if not is_method:
        return candidates[:top_k] if top_k else candidates

    terms = methodology_terms or DEFAULT_METHODOLOGY_TERMS
    rescored: List[RetrievalCandidate] = []

    for c in candidates:
        c_copy = c.model_copy()
        weight = score_candidate_priority(c_copy, is_methodology=True, methodology_terms=terms)
        base_score = c_copy.reranker_score if c_copy.reranker_score is not None else (
            c_copy.dense_score if c_copy.dense_score is not None else c_copy.final_score
        )
        
        # Boosted score clamped between 0 and 1
        adjusted_score = min(round(base_score * weight, 4), 1.0)
        c_copy.final_score = adjusted_score

        if weight > 1.0:
            c_copy.retrieval_rationale = (
                f"{c_copy.retrieval_rationale} | Methodology priority boost ({weight:.2f}x applied)"
            )
        elif weight < 1.0:
            c_copy.retrieval_rationale = (
                f"{c_copy.retrieval_rationale} | Metadata header penalty ({weight:.2f}x applied)"
            )

        rescored.append(c_copy)

    # Sort by adjusted score descending
    rescored.sort(key=lambda x: x.final_score, reverse=True)

    # Re-assign final ranks
    for new_rank, cand in enumerate(rescored, start=1):
        cand.final_rank = new_rank

    return rescored[:top_k] if top_k else rescored
