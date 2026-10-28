"""Persistent ChromaDB Vector Index manager for ResearchMind."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
import numpy as np

import chromadb
from chromadb.config import Settings as ChromaSettings

from researchmind.schemas.models import ResearchChunk, RetrievalCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)


class VectorIndexManager:
    """Manages persistent ChromaDB vector collections for baseline corpus and temporary user sessions."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: str = "researchmind_papers",
        session_collection_name: str = "lumina_session_papers",
    ):
        self.persist_dir = persist_dir or settings.vector_index_path
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.session_collection_name = session_collection_name

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )
        # Permanent baseline corpus collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        # Dedicated temporary session collection (No permanent corpus pollution)
        self.session_collection = self.client.get_or_create_collection(
            name=self.session_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Initialized ChromaDB collections: '{collection_name}' (permanent count: {self.collection.count()}), "
            f"'{session_collection_name}' (session count: {self.session_collection.count()})"
        )

    def count(self, is_session: bool = False) -> int:
        """Return total number of chunks indexed in the target vector database."""
        if is_session:
            return self.session_collection.count()
        return self.collection.count()

    def add_chunks(
        self,
        chunks: List[ResearchChunk],
        embeddings: np.ndarray,
        is_session: Optional[bool] = None,
    ) -> None:
        """Add research chunks and their corresponding embeddings to the vector collection.
        
        Args:
            chunks: List of ResearchChunk objects.
            embeddings: Numpy array of shape (len(chunks), embedding_dim).
            is_session: Explicitly store in temporary session database if True.
        """
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})")

        # Determine target collection based on scope or flag
        first_scope = getattr(chunks[0], "scope", "global")
        first_session = getattr(chunks[0], "session_id", None)
        route_to_session = is_session if is_session is not None else (first_scope in ("user", "user_papers", "session") or bool(first_session))
        target_collection = self.session_collection if route_to_session else self.collection
        db_type_label = "temporary session database" if route_to_session else "permanent corpus database"

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        embeddings_list = [emb.tolist() for emb in embeddings]

        metadatas = []
        for c in chunks:
            meta = {
                "chunk_id": c.chunk_id,
                "paper_id": c.paper_id,
                "title": c.title or "",
                "authors": json.dumps(c.authors),
                "section": c.section or "",
                "subsection": c.subsection or "",
                "page_start": c.page_start,
                "page_end": c.page_end,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
                "char_count": c.char_count,
                "scope": getattr(c, "scope", "global"),
                "session_id": getattr(c, "session_id", "") or "",
                "source": getattr(c, "source", "corpus"),
                "bbox": json.dumps(getattr(c, "bbox", [])) if getattr(c, "bbox", None) else "",
                "element_types": json.dumps(c.element_types),
            }
            metadatas.append(meta)

        # Chroma upsert in batches of 500
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            target_collection.upsert(
                ids=ids[i:end_idx],
                embeddings=embeddings_list[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx],
            )

        logger.info(f"Indexed {len(chunks)} chunks in ChromaDB {db_type_label}. Total in collection: {target_collection.count()}")

    @staticmethod
    def _format_chroma_where(where_filter: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Format dictionary into valid ChromaDB query syntax with $and for multiple clauses."""
        if not where_filter:
            return None
        cleaned = {k: v for k, v in where_filter.items() if v is not None}
        if not cleaned:
            return None
        if any(k.startswith("$") for k in cleaned.keys()):
            return cleaned
        if len(cleaned) == 1:
            return cleaned
        return {"$and": [{k: v} for k, v in cleaned.items()]}

    def _query_collection(
        self,
        collection: Any,
        emb_list: List[float],
        top_k: int,
        where_filter: Optional[Dict[str, Any]],
    ) -> List[RetrievalCandidate]:
        """Internal helper to query a specific ChromaDB collection."""
        total_in_db = collection.count()
        if total_in_db == 0:
            return []

        actual_k = min(top_k, total_in_db)
        chroma_where = self._format_chroma_where(where_filter)
        try:
            results = collection.query(
                query_embeddings=[emb_list],
                n_results=actual_k,
                where=chroma_where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"ChromaDB query with filter {chroma_where} failed ({e}). Retrying without where filter.")
            try:
                results = collection.query(
                    query_embeddings=[emb_list],
                    n_results=actual_k,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as e2:
                logger.error(f"ChromaDB unconditional query failed: {e2}")
                return []

        candidates: List[RetrievalCandidate] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return candidates

        ids = results["ids"][0]
        docs = results["documents"][0] if "documents" in results else []
        metas = results["metadatas"][0] if "metadatas" in results else []
        distances = results["distances"][0] if "distances" in results else []

        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, distances), start=1):
            similarity = round(max(0.0, min(1.0, 1.0 - dist)), 4)
            authors = json.loads(meta.get("authors", "[]")) if isinstance(meta.get("authors"), str) else meta.get("authors", [])
            bbox_raw = meta.get("bbox", "")
            bbox_parsed = None
            if bbox_raw:
                try:
                    bbox_parsed = json.loads(bbox_raw)
                except Exception:
                    bbox_parsed = None

            candidate = RetrievalCandidate(
                chunk_id=cid,
                paper_id=meta.get("paper_id", ""),
                title=meta.get("title", ""),
                authors=authors,
                section=meta.get("section", "General"),
                subsection=meta.get("subsection") or None,
                page_start=int(meta.get("page_start", 1)),
                page_end=int(meta.get("page_end", 1)),
                text=doc,
                scope=meta.get("scope", "global"),
                session_id=meta.get("session_id") or None,
                source=meta.get("source", "corpus"),
                bbox=bbox_parsed,
                dense_score=similarity,
                dense_rank=rank,
                final_score=similarity,
                final_rank=rank,
                retrieval_rationale=f"Dense vector similarity: {similarity:.3f} (Rank {rank})",
            )
            candidates.append(candidate)

        return candidates

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalCandidate]:
        """Query vector database for nearest neighbor chunks across target scopes.
        
        Args:
            query_embedding: 1D numpy array or list representing query vector.
            top_k: Number of nearest neighbors to retrieve.
            where_filter: Optional ChromaDB metadata filter dict.
            
        Returns:
            List of RetrievalCandidate objects ranked by cosine similarity.
        """
        emb_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

        # Determine target scope from where_filter
        scope_val = where_filter.get("scope") if where_filter else None
        session_val = where_filter.get("session_id") if where_filter else None

        # Scope: User session only (temporary database)
        if scope_val in ("user", "user_papers", "my_papers") or session_val:
            session_candidates = self._query_collection(self.session_collection, emb_list, top_k, where_filter)
            # Fallback to permanent collection in case legacy user chunks exist there
            if not session_candidates and self.collection.count() > 0:
                legacy_candidates = self._query_collection(self.collection, emb_list, top_k, where_filter)
                if legacy_candidates:
                    return legacy_candidates
            return session_candidates

        # Scope: Global permanent corpus only
        if scope_val == "global":
            return self._query_collection(self.collection, emb_list, top_k, where_filter)

        # Multi-scope or Unconstrained (global + user + online):
        # Query both collections and merge
        perm_candidates = self._query_collection(self.collection, emb_list, top_k, where_filter)
        session_candidates = self._query_collection(self.session_collection, emb_list, top_k, where_filter)

        merged = perm_candidates + session_candidates
        # Deduplicate by chunk_id and sort by dense_score descending
        seen = set()
        unique = []
        for c in sorted(merged, key=lambda x: x.dense_score or 0.0, reverse=True):
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                unique.append(c)
        return unique[:top_k]
