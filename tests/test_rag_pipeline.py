"""Integration tests for ResearchMind RAG pipeline across query types, evidence states, and abstention."""

import pytest
from researchmind.schemas.models import RetrievalCandidate, RetrievalMode, EvidenceStrength, Citation
from researchmind.pipeline.rag import ResearchMindRAG
from researchmind.evaluation.retrieval_metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_hit_rate_at_k,
    compute_mrr,
    compute_ndcg_at_k,
    compute_abstention_metrics,
)


class MockDenseRetriever:
    def retrieve(self, query, top_k=20, where_filter=None):
        if "out_of_domain" in query.lower() or "unsupported" in query.lower():
            return [
                RetrievalCandidate(
                    chunk_id="chunk_unrelated",
                    paper_id="paper_unrelated",
                    title="Unrelated Topic",
                    authors=["Author X"],
                    section="General",
                    page_start=1,
                    page_end=1,
                    text="This document discusses something completely unrelated to the user query.",
                    dense_score=0.15,
                    dense_rank=1,
                )
            ]
        return [
            RetrievalCandidate(
                chunk_id="chunk_01",
                paper_id="paper_001",
                title="Dense Retrieval in AI",
                authors=["Author A"],
                section="Limitations",
                page_start=5,
                page_end=5,
                text="Dense retrieval can struggle with rare technical terms and out-of-vocabulary words.",
                dense_score=0.89,
                dense_rank=1,
            )
        ]


class MockSparseRetriever:
    def retrieve(self, query, top_k=20):
        if "out_of_domain" in query.lower() or "unsupported" in query.lower():
            return []
        return [
            RetrievalCandidate(
                chunk_id="chunk_02",
                paper_id="paper_002",
                title="BM25 for Scientific Documents",
                authors=["Author B"],
                section="Keywords",
                page_start=2,
                page_end=2,
                text="BM25 excels at exact keyword matching and preserving specific scientific formulas.",
                bm25_score=14.2,
                bm25_rank=1,
            )
        ]


class MockReranker:
    def rerank(self, query, candidates, top_k=5):
        for rank, c in enumerate(candidates, start=1):
            if "unrelated" in c.chunk_id:
                c.reranker_score = 0.12
            else:
                c.reranker_score = 0.95 - (rank * 0.05)
            c.reranker_rank = rank
            c.final_rank = rank
            c.final_score = c.reranker_score
        return candidates[:top_k]


def test_rag_pipeline_end_to_end_answerable():
    """Test State A: Answerable query with high-confidence evidence."""
    rag = ResearchMindRAG(
        dense_retriever=MockDenseRetriever(),
        sparse_retriever=MockSparseRetriever(),
        reranker=MockReranker(),
    )

    response = rag.query(
        query="What are the limitations of dense retrieval?",
        retrieval_mode="hybrid_rerank",
        top_k=2,
        enable_xai=True,
    )

    assert response.query == "What are the limitations of dense retrieval?"
    assert response.retrieval_mode == "hybrid_rerank"
    assert len(response.sources) == 2
    assert response.sources[0].paper_id in ["paper_001", "paper_002"]
    assert response.xai_explanation is not None
    assert response.evidence_state in ["strong", "moderate"]
    assert response.abstained is False


def test_rag_pipeline_unanswerable_abstention():
    """Test State C: Unanswerable / out-of-domain query with low retrieval confidence."""
    rag = ResearchMindRAG(
        dense_retriever=MockDenseRetriever(),
        sparse_retriever=MockSparseRetriever(),
        reranker=MockReranker(),
    )

    response = rag.query(
        query="Out_of_domain: How to fix a carburetor in a 1970 tractor?",
        retrieval_mode="hybrid_rerank",
        top_k=1,
        enable_xai=True,
    )

    assert response.evidence_state == "insufficient"
    assert response.abstained is True
    assert (
        "insufficient evidence" in response.answer.lower()
        or "couldn't find sufficient evidence" in response.answer.lower()
        or "not find sufficient evidence" in response.answer.lower()
    )


def test_paper_vs_chunk_level_retrieval_metrics():
    """Test dual-level retrieval metric computation."""
    retrieved_paper_ids = ["p1", "p2", "p3", "p4", "p5"]
    relevant_paper_ids = {"p1", "p3"}

    recall_5 = compute_recall_at_k(retrieved_paper_ids, relevant_paper_ids, 5)
    assert recall_5 == 1.0

    hit_5 = compute_hit_rate_at_k(retrieved_paper_ids, relevant_paper_ids, 5)
    assert hit_5 == 1.0

    mrr = compute_mrr(retrieved_paper_ids, relevant_paper_ids)
    assert mrr == 1.0  # p1 is ranked #1

    # Chunk-level retrieval
    retrieved_chunk_ids = ["chk_01", "chk_02", "chk_03", "chk_04", "chk_05"]
    relevant_chunk_ids = {"chk_02", "chk_99"}  # chk_99 was not retrieved

    chunk_recall_5 = compute_recall_at_k(retrieved_chunk_ids, relevant_chunk_ids, 5)
    assert chunk_recall_5 == 0.5

    chunk_mrr = compute_mrr(retrieved_chunk_ids, relevant_chunk_ids)
    assert chunk_mrr == 0.5  # chk_02 is at rank 2 -> 1/2


def test_abstention_metrics_calculation():
    """Test abstention evaluation metric suite."""
    eval_cases = [
        {"answerability": "answerable", "abstained": False},
        {"answerability": "answerable", "abstained": False},
        {"answerability": "answerable", "abstained": True},   # False abstention
        {"answerability": "unanswerable", "abstained": True}, # Correct abstention
        {"answerability": "unanswerable", "abstained": False},# Unsupported answer
    ]

    metrics = compute_abstention_metrics(eval_cases)
    # Total = 5, Correct decisions = 2 (answered) + 1 (abstained) = 3 -> 3/5 = 0.6
    assert metrics["abstention_accuracy"] == 0.6
    assert metrics["unsupported_answer_rate"] == 0.5  # 1 out of 2 unanswerable
    assert metrics["false_abstention_rate"] == round(1 / 3, 4)  # 0.3333
