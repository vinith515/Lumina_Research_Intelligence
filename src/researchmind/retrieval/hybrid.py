"""Hybrid retriever combining dense semantic retrieval and sparse BM25 retrieval."""

import logging
from typing import List, Optional, Dict, Any

from researchmind.schemas.models import RetrievalCandidate
from researchmind.retrieval.dense import DenseRetriever
from researchmind.retrieval.sparse import SparseRetriever
from researchmind.retrieval.fusion import reciprocal_rank_fusion, weighted_score_fusion
from researchmind.config import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines Dense and BM25 retrievers with Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        rrf_k: Optional[int] = None,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.rrf_k = rrf_k or settings.RRF_K

    def retrieve(
        self,
        query: str,
        dense_top_k: Optional[int] = None,
        sparse_top_k: Optional[int] = None,
        final_top_k: Optional[int] = None,
        where_filter: Optional[Dict[str, Any]] = None,
        method: str = "rrf",
    ) -> List[RetrievalCandidate]:
        """Execute hybrid search combining Dense and Sparse retrieval with fusion.
        
        Args:
            query: User search query.
            dense_top_k: Number of dense results to retrieve.
            sparse_top_k: Number of sparse results to retrieve.
            final_top_k: Number of fused results to return.
            where_filter: Metadata filter for dense retrieval.
            method: 'rrf' or 'weighted'.
            
        Returns:
            List of fused RetrievalCandidate objects.
        """
        d_k = dense_top_k or settings.DENSE_TOP_K
        s_k = sparse_top_k or settings.SPARSE_TOP_K
        f_k = final_top_k or settings.HYBRID_TOP_K

        # Derive allowed_paper_ids and scope from where_filter if present
        allowed_paper_ids: Optional[List[str]] = None
        scope_filter: Optional[str] = None
        session_filter: Optional[str] = None

        if where_filter:
            if "paper_id" in where_filter:
                p_val = where_filter["paper_id"]
                if isinstance(p_val, str):
                    allowed_paper_ids = [p_val]
                elif isinstance(p_val, dict) and "$in" in p_val:
                    allowed_paper_ids = list(p_val["$in"])
            if "scope" in where_filter:
                scope_filter = where_filter["scope"]
            if "session_id" in where_filter:
                session_filter = where_filter["session_id"]

        # Step 1: Run Dense Retrieval (with Chroma where_filter)
        dense_results = self.dense_retriever.retrieve(query, top_k=d_k, where_filter=where_filter)

        # Step 2: Run Sparse BM25 Retrieval (with identical pre-retrieval scope filtering)
        sparse_results = self.sparse_retriever.retrieve(
            query,
            top_k=s_k,
            allowed_paper_ids=allowed_paper_ids,
            scope=scope_filter,
            session_id=session_filter,
        )

        # Step 3: Combine with Fusion
        if method == "weighted":
            fused = weighted_score_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                top_k=f_k,
            )
        else:
            fused = reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                k=self.rrf_k,
                top_k=f_k,
            )

        logger.debug(
            f"Hybrid retrieval: {len(dense_results)} dense + {len(sparse_results)} sparse -> {len(fused)} fused chunks."
        )
        return fused
