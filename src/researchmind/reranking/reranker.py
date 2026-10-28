"""Cross-Encoder Reranker for high-precision query-chunk relevance scoring."""

import logging
from typing import List, Optional
import numpy as np

from researchmind.schemas.models import RetrievalCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks retrieval candidate chunks using a Cross-Encoder transformer model."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        self.model_name = model_name or settings.RERANKER_MODEL
        self.top_k = top_k or settings.RERANKER_TOP_K
        self.device = self._resolve_device(device or settings.DEVICE)
        self._model = None

    def _resolve_device(self, requested: str) -> str:
        try:
            import torch
            if requested == "cuda" and torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    @property
    def model(self):
        """Lazy load CrossEncoder model."""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder model '{self.model_name}' on device '{self.device}'...")
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        top_k: Optional[int] = None,
    ) -> List[RetrievalCandidate]:
        """Rerank candidates using cross-attention relevance scoring.
        
        Args:
            query: User query string.
            candidates: Initial retrieval candidate chunks.
            top_k: Number of top reranked chunks to return.
            
        Returns:
            Reranked list of RetrievalCandidate objects with updated reranker scores and explanations.
        """
        if not candidates:
            return []

        k = top_k or self.top_k
        pairs = [[query, c.text] for c in candidates]

        raw_scores = self.model.predict(pairs, show_progress_bar=False)

        # Sigmoid activation to normalize cross-encoder logits to [0, 1]
        probs = 1.0 / (1.0 + np.exp(-np.asarray(raw_scores, dtype=np.float32)))

        scored_candidates: List[RetrievalCandidate] = []
        for cand, prob in zip(candidates, probs):
            cand_copy = cand.model_copy()
            cand_copy.reranker_score = round(float(prob), 4)
            scored_candidates.append(cand_copy)

        # Sort by reranker score descending
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda x: x.reranker_score if x.reranker_score is not None else 0.0,
            reverse=True,
        )[:k]

        for new_rank, cand in enumerate(sorted_candidates, start=1):
            cand.reranker_rank = new_rank
            cand.final_score = cand.reranker_score
            cand.final_rank = new_rank

            prev_rank_str = f"RRF rank #{cand.rrf_rank}" if cand.rrf_rank else (
                f"Dense #{cand.dense_rank}" if cand.dense_rank else f"BM25 #{cand.bm25_rank}"
            )
            cand.retrieval_rationale = (
                f"Cross-encoder relevance: {cand.reranker_score:.3f} (Reranked #{new_rank} from {prev_rank_str})"
            )

        logger.debug(f"Reranked {len(candidates)} candidates down to top {len(sorted_candidates)}")
        return sorted_candidates
