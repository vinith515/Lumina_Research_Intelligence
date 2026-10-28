"""Unit and integration tests for Advanced Explainable AI (XAI) features."""

import pytest
from researchmind.schemas.models import (
    RetrievalCandidate,
    StructuredCitation,
    Citation,
    CitationScoreBreakdown,
    XAIExplanation,
    ClaimExplanation,
    GroundingAssessment,
    ComponentQualityAssessment,
    EvidenceStrength,
)
from researchmind.pipeline.rag import extract_matched_keywords
from researchmind.xai.explainer import ResearchXAIExplainer


def test_extract_matched_keywords():
    query = "How does FlashAttention avoid the quadratic memory overhead of standard self-attention?"
    passage = "FlashAttention utilizes an IO-aware tiling technique that eliminates the quadratic memory footprint of standard self-attention mechanisms."
    matched = extract_matched_keywords(query, passage)
    assert "flashattention" in matched
    assert "quadratic" in matched
    assert "memory" in matched
    assert "self-attention" in matched
    # Stopwords like 'the', 'how', 'does', 'of' should not be present
    assert "the" not in matched
    assert "does" not in matched


def test_citation_score_breakdown_and_provenance():
    bd = CitationScoreBreakdown(
        dense_score=0.842,
        dense_rank=1,
        bm25_score=19.4,
        bm25_rank=2,
        rrf_score=0.0325,
        rrf_rank=1,
        reranker_score=0.912,
        reranker_rank=1,
        final_confidence=91.2,
        section_boost_applied=0.1,
    )
    assert bd.dense_score == 0.842
    assert bd.bm25_score == 19.4
    assert bd.reranker_score == 0.912
    assert bd.final_confidence == 91.2

    citation = StructuredCitation(
        citation_id="C1",
        paper_id="2205.14135",
        title="FlashAttention: Fast and Memory-Efficient Exact Attention",
        authors=["Tri Dao", "Daniel Y. Fu"],
        page_start=1,
        page_end=2,
        section="Methodology",
        chunk_id="chunk_001",
        retrieval_score=0.912,
        score_breakdown=bd,
        selection_rationale="Selected due to top-ranked Cross-Encoder score and direct technical alignment.",
        matched_keywords=["flashattention", "memory", "tiling"],
        supported_claims=[1, 2],
    )
    assert citation.citation_id == "C1"
    assert citation.score_breakdown.reranker_score == 0.912
    assert "flashattention" in citation.matched_keywords
    assert 1 in citation.supported_claims
    assert 2 in citation.supported_claims
    assert "Selected" in citation.selection_rationale


def test_xai_explainer_generates_comprehensive_report():
    explainer = ResearchXAIExplainer()

    cand1 = RetrievalCandidate(
        chunk_id="chunk_1",
        paper_id="paper_1",
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        page_start=3,
        page_end=4,
        section="Model Architecture",
        text="The Transformer relies entirely on self-attention to compute representations of its input and output.",
        dense_score=0.88,
        dense_rank=1,
        bm25_score=22.0,
        bm25_rank=1,
        rrf_score=0.033,
        rrf_rank=1,
        reranker_score=0.95,
        final_score=0.95,
        final_rank=1,
    )

    query = "What is the Transformer architecture based on?"
    answer = "The Transformer model uses self-attention layers to compute representations of input and output."

    report: XAIExplanation = explainer.generate_explanation(
        query=query,
        answer=answer,
        dense_results=[cand1],
        sparse_results=[cand1],
        hybrid_results=[cand1],
        final_evidence=[cand1],
        target_paper_id="paper_1",
        target_paper_title="Attention Is All You Need",
    )

    assert report is not None
    assert isinstance(report, XAIExplanation)
    assert report.faithfulness_score > 0
    assert "total_corpus_chunks" in report.retrieval_funnel
    assert len(report.contrastive_insights) > 0
    assert "C1" in report.citation_rationales
    assert "Attention Is All You Need" in report.citation_rationales["C1"]
    assert report.grounding.evidence_strength_overall in [EvidenceStrength.STRONG, EvidenceStrength.MODERATE]
