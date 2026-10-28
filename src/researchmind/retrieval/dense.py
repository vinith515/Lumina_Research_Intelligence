"""Dense vector retriever using embedding model and persistent ChromaDB index."""

import logging
from typing import List, Optional, Dict, Any

from researchmind.schemas.models import RetrievalCandidate
from researchmind.embeddings.embedder import ResearchEmbedder
from researchmind.indexing.vector_index import VectorIndexManager
from researchmind.config import settings

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Performs dense semantic retrieval over embedded research chunks."""

    def __init__(
        self,
        embedder: Optional[ResearchEmbedder] = None,
        index_manager: Optional[VectorIndexManager] = None,
    ):
        self.embedder = embedder or ResearchEmbedder()
        self.index_manager = index_manager or VectorIndexManager()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalCandidate]:
        """Execute dense vector similarity retrieval.
        
        Args:
            query: Query string.
            top_k: Number of chunks to retrieve.
            where_filter: Optional metadata filtering dictionary.
            
        Returns:
            List of RetrievalCandidate objects ranked by cosine similarity.
        """
        k = top_k or settings.DENSE_TOP_K
        query_emb = self.embedder.embed_query(query)
        candidates = self.index_manager.query(query_emb, top_k=k, where_filter=where_filter)
        logger.debug(f"Dense retriever returned {len(candidates)} candidates for query: '{query[:40]}...'")
        return candidates
