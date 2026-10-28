"""Unit tests for Explainable AI (XAI) engine, Claim Grounding, and Evidence Verification."""

from researchmind.schemas.models import RetrievalCandidate, EvidenceStrength, Citation
from researchmind.xai.grounding import GroundingVerifier, extract_claims
from researchmind.xai.evidence_strength import calculate_evidence_strength
from researchmind.xai.explainer import ResearchXAIExplainer


def test_extract_claims():
    text = (
        "Dense retrieval struggles with out-of-vocabulary terminology [1]. "
        "However, hybrid retrieval with BM25 alleviates this problem significantly [2]. "
        "Overall, combining methods yields better performance."
    )
    claims = extract_claims(text)
    assert len(claims) == 3


def test_evidence_strength_strong():
    cand1 = RetrievalCandidate(
        chunk_id="chk_1", paper_id="p1", title="Title 1", section="Method", page_start=1, page_end=1, text="Text",
        reranker_score=0.88, dense_rank=1, bm25_rank=1,
    )
    cand2 = RetrievalCandidate(
        chunk_id="chk_2", paper_id="p2", title="Title 2", section="Method", page_start=2, page_end=2, text="Text",
        reranker_score=0.78, dense_rank=2, bm25_rank=2,
    )
    strength, desc = calculate_evidence_strength([cand1, cand2], min_score_threshold=0.35)
    assert strength == EvidenceStrength.STRONG


def test_evidence_strength_insufficient_threshold():
    cand1 = RetrievalCandidate(
        chunk_id="chk_low", paper_id="p_low", title="Weak Match", section="Intro", page_start=1, page_end=1, text="Vague text",
        reranker_score=0.22,
    )
    strength, desc = calculate_evidence_strength([cand1], min_score_threshold=0.35)
    assert strength == EvidenceStrength.INSUFFICIENT


def test_grounding_verifier_supported_and_unsupported_claims():
    cand = RetrievalCandidate(
        chunk_id="chk_1",
        paper_id="p1",
        title="Distillation Paper",
        section="Method",
        page_start=3,
        page_end=3,
        text="We propose an on-policy distillation framework that leverages reference images during training.",
        final_score=0.85,
    )
    verifier = GroundingVerifier(token_overlap_threshold=0.30)
    
    # Grounded claim + unsupported hallucinated claim
    answer = (
        "The authors propose an on-policy distillation framework utilizing reference images during training. "
        "Furthermore, they tested the method on flying lunar orbiters in outer space."
    )

    claims, assessment = verifier.verify_grounding(answer=answer, evidence_chunks=[cand])
    assert len(claims) == 2
    assert claims[0].is_grounded is True
    assert claims[1].is_grounded is False
    assert assessment.supported_claims == 1
    assert assessment.unsupported_claims == 1
    assert assessment.grounded_ratio == 0.5
    assert assessment.hallucination_warning is not None


def test_xai_explainer_report_generation():
    cand = RetrievalCandidate(
        chunk_id="chk_1",
        paper_id="p1",
        title="Sample Paper Title",
        section="Introduction",
        page_start=1,
        page_end=2,
        text="Dense embeddings capture semantic context across scientific text.",
        final_score=0.85,
        reranker_score=0.85,
    )
    explainer = ResearchXAIExplainer()
    xai = explainer.generate_explanation(
        query="What do dense embeddings capture?",
        answer="Dense embeddings capture semantic context across scientific text [1].",
        dense_results=[cand],
        sparse_results=[],
        hybrid_results=[cand],
        final_evidence=[cand],
    )

    assert xai.evidence_strength in [EvidenceStrength.STRONG, EvidenceStrength.MODERATE]
    assert xai.abstained is False
    assert len(xai.claim_explanations) >= 1
    assert "🔬 RESEARCHMIND EXPLAINABLE AI" in xai.human_readable_report
