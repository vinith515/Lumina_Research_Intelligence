"""Reciprocal Rank Fusion (RRF) and Weighted Score Fusion algorithms."""

import logging
from typing import List, Dict, Optional
from researchmind.schemas.models import RetrievalCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    dense_results: List[RetrievalCandidate],
    sparse_results: List[RetrievalCandidate],
    k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
    top_k: int = 20,
) -> List[RetrievalCandidate]:
    """Combine ranked dense and sparse candidates using Reciprocal Rank Fusion (RRF).
    
    Formula:
        RRF_score(d) = (w_dense / (k + rank_dense(d))) + (w_sparse / (k + rank_sparse(d)))
        
    Args:
        dense_results: Ranked candidates from dense retrieval.
        sparse_results: Ranked candidates from BM25 retrieval.
        k: RRF constant parameter (default 60).
        dense_weight: Multiplier weight for dense retrieval.
        sparse_weight: Multiplier weight for sparse retrieval.
        top_k: Number of fused candidates to return.
        
    Returns:
        List of fused RetrievalCandidate objects with updated rrf_score, rrf_rank, and rationale.
    """
    candidate_map: Dict[str, RetrievalCandidate] = {}
    rrf_scores: Dict[str, float] = {}

    # Accumulate Dense RRF scores
    for rank, cand in enumerate(dense_results, start=1):
        cid = cand.chunk_id
        candidate_map[cid] = cand.model_copy()
        candidate_map[cid].dense_rank = rank
        candidate_map[cid].dense_score = cand.dense_score
        score_contrib = dense_weight / (k + rank)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score_contrib

    # Accumulate Sparse RRF scores
    for rank, cand in enumerate(sparse_results, start=1):
        cid = cand.chunk_id
        if cid not in candidate_map:
            candidate_map[cid] = cand.model_copy()
        candidate_map[cid].bm25_rank = rank
        candidate_map[cid].bm25_score = cand.bm25_score
        score_contrib = sparse_weight / (k + rank)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score_contrib

    # Sort all unique candidates by descending RRF score
    sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    fused_results: List[RetrievalCandidate] = []
    for final_rank, cid in enumerate(sorted_cids, start=1):
        cand = candidate_map[cid]
        cand.rrf_score = round(rrf_scores[cid], 6)
        cand.rrf_rank = final_rank
        cand.final_score = cand.rrf_score
        cand.final_rank = final_rank

        # Human-readable rationale
        in_dense = cand.dense_rank is not None
        in_bm25 = cand.bm25_rank is not None

        dense_sc = cand.dense_score if cand.dense_score is not None else 0.0
        bm25_sc = cand.bm25_score if cand.bm25_score is not None else 0.0

        if in_dense and in_bm25:
            cand.retrieval_rationale = (
                f"Dual consensus: ranked #{cand.dense_rank} in dense (score: {dense_sc:.3f}) "
                f"and #{cand.bm25_rank} in BM25 (score: {bm25_sc:.2f}) -> RRF: {cand.rrf_score:.5f}"
            )
        elif in_dense:
            cand.retrieval_rationale = (
                f"Dense semantic match: ranked #{cand.dense_rank} in dense (score: {dense_sc:.3f}) -> RRF: {cand.rrf_score:.5f}"
            )
        else:
            cand.retrieval_rationale = (
                f"Keyword BM25 match: ranked #{cand.bm25_rank} in BM25 (score: {bm25_sc:.2f}) -> RRF: {cand.rrf_score:.5f}"
            )

        fused_results.append(cand)

    return fused_results


def weighted_score_fusion(
    dense_results: List[RetrievalCandidate],
    sparse_results: List[RetrievalCandidate],
    dense_weight: float = 0.5,
    sparse_weight: float = 0.5,
    top_k: int = 20,
) -> List[RetrievalCandidate]:
    """Combine candidates via Min-Max Normalized Weighted Score Fusion."""
    candidate_map: Dict[str, RetrievalCandidate] = {}
    dense_norm: Dict[str, float] = {}
    sparse_norm: Dict[str, float] = {}

    # Dense scores (already cosine similarity 0-1)
    for rank, cand in enumerate(dense_results, start=1):
        cid = cand.chunk_id
        candidate_map[cid] = cand.model_copy()
        candidate_map[cid].dense_rank = rank
        candidate_map[cid].dense_score = cand.dense_score
        dense_norm[cid] = cand.dense_score if cand.dense_score is not None else 0.0

    # BM25 scores (min-max normalize)
    if sparse_results:
        raw_bm25 = [c.bm25_score for c in sparse_results if c.bm25_score is not None]
        min_b, max_b = min(raw_bm25, default=0.0), max(raw_bm25, default=1.0)
        denom = max(max_b - min_b, 1e-6)
        for rank, cand in enumerate(sparse_results, start=1):
            cid = cand.chunk_id
            if cid not in candidate_map:
                candidate_map[cid] = cand.model_copy()
            candidate_map[cid].bm25_rank = rank
            candidate_map[cid].bm25_score = cand.bm25_score
            sparse_norm[cid] = ((cand.bm25_score or 0.0) - min_b) / denom

    fused_scores: Dict[str, float] = {}
    for cid in candidate_map.keys():
        d_score = dense_norm.get(cid, 0.0)
        s_score = sparse_norm.get(cid, 0.0)
        fused_scores[cid] = (dense_weight * d_score) + (sparse_weight * s_score)

    sorted_cids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)[:top_k]

    fused_results: List[RetrievalCandidate] = []
    for final_rank, cid in enumerate(sorted_cids, start=1):
        cand = candidate_map[cid]
        cand.final_score = round(fused_scores[cid], 4)
        cand.final_rank = final_rank
        fused_results.append(cand)

    return fused_results
