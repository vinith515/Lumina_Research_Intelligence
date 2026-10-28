"""Unit tests for Fusion algorithms (RRF, Weighted) and Ranking signals."""

from researchmind.schemas.models import RetrievalCandidate
from researchmind.retrieval.fusion import reciprocal_rank_fusion, weighted_score_fusion


def test_reciprocal_rank_fusion():
    dense_cand1 = RetrievalCandidate(
        chunk_id="chunk_01",
        paper_id="paper_a",
        title="Paper A",
        section="Intro",
        page_start=1,
        page_end=1,
        text="Dense high relevance text",
        dense_score=0.92,
        dense_rank=1,
    )
    dense_cand2 = RetrievalCandidate(
        chunk_id="chunk_02",
        paper_id="paper_b",
        title="Paper B",
        section="Method",
        page_start=2,
        page_end=2,
        text="Dense medium text",
        dense_score=0.81,
        dense_rank=2,
    )

    sparse_cand1 = RetrievalCandidate(
        chunk_id="chunk_02",  # present in both
        paper_id="paper_b",
        title="Paper B",
        section="Method",
        page_start=2,
        page_end=2,
        text="Dense medium text",
        bm25_score=15.4,
        bm25_rank=1,
    )
    sparse_cand3 = RetrievalCandidate(
        chunk_id="chunk_03",
        paper_id="paper_c",
        title="Paper C",
        section="Results",
        page_start=5,
        page_end=5,
        text="BM25 only text",
        bm25_score=12.1,
        bm25_rank=2,
    )

    fused = reciprocal_rank_fusion(
        dense_results=[dense_cand1, dense_cand2],
        sparse_results=[sparse_cand1, sparse_cand3],
        k=60,
        top_k=5,
    )

    assert len(fused) == 3
    # chunk_02 is in both dense (#2) and sparse (#1), so it should have the highest RRF score!
    # RRF(chunk_02) = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.03252
    # RRF(chunk_01) = 1/(60+1) = 0.016393
    # RRF(chunk_03) = 1/(60+2) = 0.016129
    assert fused[0].chunk_id == "chunk_02"
    assert fused[0].final_rank == 1
    assert "Dual consensus" in fused[0].retrieval_rationale


def test_weighted_score_fusion():
    dense_cand1 = RetrievalCandidate(
        chunk_id="chunk_01",
        paper_id="paper_a",
        title="Paper A",
        section="Intro",
        page_start=1,
        page_end=1,
        text="Text",
        dense_score=0.90,
        dense_rank=1,
    )
    sparse_cand1 = RetrievalCandidate(
        chunk_id="chunk_01",
        paper_id="paper_a",
        title="Paper A",
        section="Intro",
        page_start=1,
        page_end=1,
        text="Text",
        bm25_score=10.0,
        bm25_rank=1,
    )

    fused = weighted_score_fusion([dense_cand1], [sparse_cand1], top_k=2)
    assert len(fused) == 1
    assert fused[0].final_score > 0.0
