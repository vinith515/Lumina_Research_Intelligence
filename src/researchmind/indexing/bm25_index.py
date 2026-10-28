"""Persistent BM25 Sparse Index manager preserving scientific and technical terminology."""

import json
import logging
import pickle
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from rank_bm25 import BM25Plus

from researchmind.schemas.models import ResearchChunk, RetrievalCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)


def scientific_tokenize(text: str) -> List[str]:
    """Tokenize technical and scientific text preserving hyphens, acronyms, and alphanumeric terms."""
    if not text:
        return []
    # Match words with embedded hyphens/underscores/dots (e.g., 'zero-shot', 'ResNet-50', 'F1-score', 'v1.5')
    tokens = re.findall(r"\b[a-zA-Z0-9]+(?:[-_\.][a-zA-Z0-9]+)*\b", text.lower())
    return [t for t in tokens if len(t) > 1]


class BM25IndexManager:
    """Manages persistent BM25 sparse index for scientific research chunks."""

    def __init__(
        self,
        index_dir: Optional[Path] = None,
    ):
        self.index_dir = index_dir or settings.bm25_index_path
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.model_file = self.index_dir / "bm25_model.pkl"
        self.meta_file = self.index_dir / "bm25_chunks.json"

        self.bm25: Optional[BM25Plus] = None
        self.chunks_data: List[Dict[str, Any]] = []

        if self.model_file.exists() and self.meta_file.exists():
            self.load()

    def count(self) -> int:
        """Return total number of chunks in BM25 index."""
        return len(self.chunks_data)

    def build_index(self, chunks: List[ResearchChunk]) -> None:
        """Build and persist BM25 index over research chunks.
        
        Args:
            chunks: List of ResearchChunk objects.
        """
        if not chunks:
            logger.warning("No chunks provided to build BM25 index.")
            return

        logger.info(f"Building BM25 sparse index over {len(chunks)} research chunks...")
        corpus_tokens = [scientific_tokenize(c.text) for c in chunks]

        self.bm25 = BM25Plus(corpus_tokens)
        self.chunks_data = [c.model_dump() for c in chunks]

        self.save()
        logger.info(f"Successfully built and persisted BM25 index ({len(chunks)} documents).")

    def save(self) -> None:
        """Save BM25 model and chunk metadata to disk."""
        with open(self.model_file, "wb") as f:
            pickle.dump(self.bm25, f)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.chunks_data, f)
        logger.debug(f"Saved BM25 index to {self.index_dir}")

    def load(self) -> None:
        """Load BM25 model and chunk metadata from disk."""
        try:
            with open(self.model_file, "rb") as f:
                self.bm25 = pickle.load(f)
            with open(self.meta_file, "r", encoding="utf-8") as f:
                self.chunks_data = json.load(f)
            logger.info(f"Loaded BM25 index with {len(self.chunks_data)} chunks from {self.index_dir}")
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            self.bm25 = None
            self.chunks_data = []

    def add_chunks(self, new_chunks: List[ResearchChunk]) -> None:
        """Incrementally append new chunks to the BM25 index and refresh the BM25Plus model."""
        if not new_chunks:
            return

        existing_cids = {c["chunk_id"] for c in self.chunks_data}
        unique_new = [c for c in new_chunks if c.chunk_id not in existing_cids]
        if not unique_new:
            logger.info("All chunks already present in BM25 index. Skipping duplicate insertion.")
            return

        for c in unique_new:
            self.chunks_data.append(c.model_dump())

        corpus_tokens = [scientific_tokenize(c["text"]) for c in self.chunks_data]
        self.bm25 = BM25Plus(corpus_tokens)
        self.save()
        logger.info(f"Incrementally added {len(unique_new)} chunks to BM25 index. Total chunks: {len(self.chunks_data)}")

    def query(
        self,
        query_text: str,
        top_k: int = 20,
        allowed_paper_ids: Optional[List[str]] = None,
        scope: Optional[str] = None,
        session_id: Optional[str] = None,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalCandidate]:
        """Query BM25 sparse index with optional pre-retrieval scope and paper filtering.
        
        Args:
            query_text: User search query.
            top_k: Number of results to retrieve.
            allowed_paper_ids: Optional list of paper IDs to restrict candidate evaluation.
            scope: Optional scope restriction ('user' or 'global').
            session_id: Optional session identifier for user uploads.
            where_filter: Optional Chroma-compatible metadata filter dictionary.
            
        Returns:
            List of RetrievalCandidate objects ranked by BM25 score.
        """
        if not self.bm25 or not self.chunks_data:
            return []

        tokens = scientific_tokenize(query_text)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        # Parse where_filter if provided
        if where_filter:
            if "scope" in where_filter:
                scope = where_filter["scope"]
            if "session_id" in where_filter:
                session_id = where_filter["session_id"]
            if "paper_id" in where_filter:
                p_filter = where_filter["paper_id"]
                if isinstance(p_filter, dict) and "$in" in p_filter:
                    allowed_paper_ids = list(p_filter["$in"])
                elif isinstance(p_filter, str):
                    allowed_paper_ids = [p_filter]

        # Pre-filter candidate indices by allowed scope/papers if specified
        valid_indices = []
        allowed_set = set(allowed_paper_ids) if allowed_paper_ids else None

        for idx, c_dict in enumerate(self.chunks_data):
            if allowed_set and c_dict.get("paper_id") not in allowed_set:
                continue
            if scope:
                chunk_scope = c_dict.get("scope", "global")
                user_scopes = {"user", "user_papers", "my_papers"}
                if scope in user_scopes and chunk_scope not in user_scopes:
                    continue
                elif scope == "global" and chunk_scope != "global":
                    continue
                elif scope not in user_scopes and scope != "global" and chunk_scope != scope:
                    continue
            if session_id and c_dict.get("session_id") and c_dict.get("session_id") != session_id:
                continue
            valid_indices.append(idx)

        if not valid_indices:
            return []

        # Sort filtered candidate indices by BM25 score
        top_indices = sorted(valid_indices, key=lambda i: scores[i], reverse=True)[:top_k]

        candidates: List[RetrievalCandidate] = []
        for rank, idx in enumerate(top_indices, start=1):
            score = float(scores[idx])
            if score <= 0:
                continue

            c_dict = self.chunks_data[idx]
            authors = c_dict.get("authors", [])

            candidate = RetrievalCandidate(
                chunk_id=c_dict["chunk_id"],
                paper_id=c_dict["paper_id"],
                title=c_dict.get("title", ""),
                authors=authors,
                section=c_dict.get("section", "General"),
                subsection=c_dict.get("subsection"),
                page_start=int(c_dict.get("page_start", 1)),
                page_end=int(c_dict.get("page_end", 1)),
                text=c_dict.get("text", ""),
                scope=c_dict.get("scope", "global"),
                session_id=c_dict.get("session_id"),
                source=c_dict.get("source", "corpus"),
                bbox=c_dict.get("bbox"),
                bm25_score=round(score, 4),
                bm25_rank=rank,
                final_score=round(score, 4),
                final_rank=rank,
                retrieval_rationale=f"BM25 keyword relevance score: {score:.2f} (Rank {rank})",
            )
            candidates.append(candidate)

        return candidates
