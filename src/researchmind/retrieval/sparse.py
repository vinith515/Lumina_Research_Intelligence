"""Sparse BM25 retriever for scientific terminology matching."""

import logging
from typing import List, Optional

from researchmind.schemas.models import RetrievalCandidate
from researchmind.indexing.bm25_index import BM25IndexManager
from researchmind.config import settings

logger = logging.getLogger(__name__)


class SparseRetriever:
    """Performs sparse keyword-based retrieval using BM25Okapi over tokenized chunks."""

    def __init__(
        self,
        index_manager: Optional[BM25IndexManager] = None,
    ):
        self.index_manager = index_manager or BM25IndexManager()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        allowed_paper_ids: Optional[List[str]] = None,
        scope: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[RetrievalCandidate]:
        """Execute BM25 keyword matching retrieval with optional pre-filtering.
        
        Args:
            query: Query string.
            top_k: Number of chunks to retrieve.
            allowed_paper_ids: Optional list of paper IDs to restrict candidate evaluation.
            scope: Optional scope filter ('user' or 'global').
            session_id: Optional user session identifier.
            
        Returns:
            List of RetrievalCandidate objects ranked by BM25 score.
        """
        k = top_k or settings.SPARSE_TOP_K
        candidates = self.index_manager.query(
            query,
            top_k=k,
            allowed_paper_ids=allowed_paper_ids,
            scope=scope,
            session_id=session_id,
        )
        logger.debug(f"Sparse retriever returned {len(candidates)} candidates for query: '{query[:40]}...'")
        return candidates
