"""Tests for target-paper filtering, methodology prioritization, 3-way claim verification, and structured fallback."""

import pytest
from researchmind.schemas.models import (
    RetrievalCandidate,
    EvidenceStrength,
    ComponentQualityAssessment,
)
from researchmind.retrieval.target_paper import (
    identify_target_paper,
    TargetPaperMatch,
    PaperCatalogRegistry,
)
from researchmind.retrieval.prioritization import (
    is_methodology_query,
    score_candidate_priority,
    prioritize_candidates,
    DEFAULT_METHODOLOGY_TERMS,
)
from researchmind.xai.grounding import GroundingVerifier, extract_claims
from researchmind.xai.evidence_strength import (
    evaluate_component_quality,
    calculate_evidence_strength,
)
from researchmind.generation.generator import LLMGenerator
from researchmind.pipeline.rag import ResearchMindRAG


def test_target_paper_identification_exact():
    """Requirement A: Test exact paper title match from query."""
    query = (
        "What is the technique followed in the research paper "
        "GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING?"
    )
    match = identify_target_paper(query)
    assert match is not None
    assert match.paper_id == "paper_0853d9c3ae9c"
    assert match.is_explicit_target_query is True
    assert match.needs_clarification is False
    assert match.confidence >= 0.90


def test_target_paper_identification_fuzzy():
    """Requirement A: Test fuzzy matching when paper title has minor variations."""
    query = "In the research paper post-segmentation quality validation of building footprints, how is error detected?"
    match = identify_target_paper(query)
    assert match is not None
    assert match.paper_id == "paper_0853d9c3ae9c"
    assert match.needs_clarification is False


def test_target_paper_ambiguous_clarification():
    """Requirement A: Test that ambiguous explicit paper queries trigger clarification request."""
    query = "What did the research paper find in its experimental evaluation of completely unknown alien signals?"
    match = identify_target_paper(query)
    assert match is not None
    assert match.is_explicit_target_query is True
    assert match.needs_clarification is True
    assert "clarify which paper" in match.clarification_message.lower()


def test_general_query_no_target_paper():
    """Requirement A: Test that general queries do not falsely bind to a target paper."""
    query = "What common techniques are used across the NLP papers?"
    match = identify_target_paper(query)
    assert match is None


def test_methodology_section_prioritization():
    """Requirement B: Test methodology sections are prioritized over metadata headers."""
    query = "What is the technique followed in the research paper?"
    assert is_methodology_query(query) is True

    c_header = RetrievalCandidate(
        chunk_id="chk_header",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=["Author A"],
        section="Introduction / Header",
        page_start=1,
        page_end=1,
        text="Department of Computer Science and Engineering, Jahangirnagar University, Dhaka 1342, Bangladesh.",
        final_score=0.98,
        reranker_score=0.98,
    )

    c_method = RetrievalCandidate(
        chunk_id="chk_method",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=["Author A"],
        section="2 Materials and Methods",
        page_start=3,
        page_end=3,
        text="The workflow combined deep-learning semantic segmentation using U-Net and SAM-LoRA with object-level machine learning.",
        final_score=0.85,
        reranker_score=0.85,
    )

    prioritized = prioritize_candidates([c_header, c_method], query=query)
    # The methodology chunk should be boosted above the header chunk
    assert prioritized[0].chunk_id == "chk_method"
    assert prioritized[1].chunk_id == "chk_header"
    assert "Methodology priority boost" in prioritized[0].retrieval_rationale


def test_claim_level_3_way_verification():
    """Requirement C: Test 3-way check (passage support, question relevance, target paper)."""
    verifier = GroundingVerifier()

    cand_target = RetrievalCandidate(
        chunk_id="chk_target",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=[],
        section="2 Materials and Methods",
        page_start=3,
        page_end=3,
        text="The workflow combined deep-learning semantic segmentation using U-Net and SAM-LoRA with spatial feature engineering.",
        final_score=0.95,
    )

    cand_other = RetrievalCandidate(
        chunk_id="chk_other",
        paper_id="paper_unrelated",
        title="Unrelated Paper",
        authors=[],
        section="Method",
        page_start=1,
        page_end=1,
        text="We apply magnetic resonance imaging algorithms to detect biological tissue structures.",
        final_score=0.90,
    )

    # Claim 1: Valid technical claim matching target paper and answering question
    # Claim 2: Metadata/affiliation statement not answering the question
    # Claim 3: Claim grounded in unrelated paper (cross-paper contamination)
    answer = (
        "1. The workflow combined deep-learning semantic segmentation using U-Net and SAM-LoRA with spatial feature engineering. [1, p.3]\n"
        "2. Department of Computer Science and Engineering, Jahangirnagar University, Dhaka 1342, Bangladesh. [1, p.1]\n"
        "3. We apply magnetic resonance imaging algorithms to detect biological tissue structures. [2, p.1]"
    )

    explanations, assessment = verifier.verify_grounding(
        answer=answer,
        evidence_chunks=[cand_target, cand_other],
        query="What is the technique followed in the research paper?",
        target_paper_id="paper_0853d9c3ae9c",
    )

    assert len(explanations) == 3

    # Claim 1 should pass all 3 checks
    assert explanations[0].is_supported_by_passage is True
    assert explanations[0].answers_question is True
    assert explanations[0].belongs_to_target_paper is True
    assert explanations[0].is_grounded is True

    # Claim 2 should fail question relevance check (metadata/affiliation)
    assert explanations[1].answers_question is False
    assert explanations[1].is_grounded is False

    # Claim 3 should fail target paper check (belongs to paper_unrelated)
    assert explanations[2].belongs_to_target_paper is False
    assert explanations[2].is_grounded is False


def test_structured_methodology_fallback():
    """Requirement D: Test structured fallback produces required sections and disclosure."""
    gen = LLMGenerator(provider="offline")
    cand = RetrievalCandidate(
        chunk_id="chk_01",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=[],
        section="2 Materials and Methods",
        subsection="2.2 Deep learning",
        page_start=3,
        page_end=3,
        text="The workflow combined deep-learning semantic segmentation using U-Net and SAM-LoRA. Then, predicted masks were transformed into vector footprints and geometrically regularized.",
        final_score=0.92,
    )

    match = TargetPaperMatch(
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        confidence=1.0,
        is_explicit_target_query=True,
    )

    answer, usage = gen.generate(
        query="What is the technique followed in the research paper?",
        candidates=[cand],
        target_paper=match,
    )

    assert "**Question Type**: Methodology Extraction" in answer
    assert "### Short Direct Answer" in answer
    assert "### Ordered Methodology Steps" in answer
    assert "### Missing-Evidence Disclosure" in answer
    assert "[1, p.3]" in answer


def test_evidence_strength_component_assessment():
    """Requirement E: Test qualitative component assessment and evidence strength recalibration."""
    cand_target = RetrievalCandidate(
        chunk_id="chk_01",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=[],
        section="Introduction / Header",
        page_start=1,
        page_end=1,
        text="Department of Computer Science and Engineering. arXiv:2608.09048v1 [cs.CV] 10 Aug 2026.",
        final_score=0.95,
        reranker_score=0.95,
    )

    cand_target_2 = RetrievalCandidate(
        chunk_id="chk_02",
        paper_id="paper_0853d9c3ae9c",
        title="GeoAI Building Footprints",
        authors=[],
        section="Introduction / Header",
        page_start=1,
        page_end=1,
        text="Department of Computer Science and Engineering. Vol 1.",
        final_score=0.90,
        reranker_score=0.90,
    )
    candidates = [cand_target, cand_target_2]

    # When Gemini fails and methodology chunks are missing:
    comp = evaluate_component_quality(
        candidates=candidates,
        query="What is the technique followed in the research paper?",
        target_paper_id="paper_0853d9c3ae9c",
        provider_status="fallback_temporary_unavailable",
        grounding_supported=0,
        grounding_total=1,
    )

    assert comp.gemini_availability == "Failed temporarily; fallback activated"
    assert comp.citation_generation == "Functioning"
    assert comp.target_paper_relevance == "Verified"
    assert comp.methodology_extraction == "Insufficient"
    assert comp.cross_paper_contamination == "None detected"
    assert comp.overall_answer_quality == "Needs improvement"

    # calculate_evidence_strength must NOT report Strong
    strength, rationale = calculate_evidence_strength(
        candidates=candidates,
        component_assessment=comp,
    )
    assert strength != EvidenceStrength.STRONG
    assert strength == EvidenceStrength.MODERATE
    assert "Calibrated from Strong to Moderate" in rationale

