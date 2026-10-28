"""Embedding generation with GPU/CPU support, batching, normalization, and persistent caching."""

import hashlib
import logging
import pickle
from pathlib import Path
from typing import List, Optional, Union
import numpy as np

from researchmind.config import settings

logger = logging.getLogger(__name__)


class ResearchEmbedder:
    """Independent embedding module with GPU/CPU acceleration, batching, and on-disk caching."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
        normalize: Optional[bool] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self.normalize = normalize if normalize is not None else settings.NORMALIZE_EMBEDDINGS
        self.cache_dir = cache_dir or (settings.PROJECT_ROOT / ".cache" / "embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Device determination
        requested_device = device or settings.DEVICE
        self.device = self._resolve_device(requested_device)
        self._model = None

    def _resolve_device(self, requested: str) -> str:
        """Resolve device to cuda if available, otherwise cpu."""
        try:
            import torch
            if requested == "cuda" and torch.cuda.is_available():
                logger.info(f"Using GPU device: {torch.cuda.get_device_name(0)}")
                return "cuda"
        except Exception:
            pass
        logger.info("Using CPU for embeddings.")
        return "cpu"

    @property
    def model(self):
        """Lazy load SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'...")
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256((self.model_name + "::" + text).encode("utf-8")).hexdigest()

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a search query.
        
        Args:
            query: Query string.
            
        Returns:
            1D numpy array of shape (embedding_dim,).
        """
        emb = self.model.encode(
            query,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            device=self.device,
        )
        return np.asarray(emb, dtype=np.float32)

    def embed_documents(
        self,
        texts: List[str],
        show_progress: bool = True,
        use_cache: bool = True,
    ) -> np.ndarray:
        """Generate embeddings for a list of document chunks with optional caching and batching.
        
        Args:
            texts: List of text chunks.
            show_progress: Whether to display tqdm progress bar.
            use_cache: Whether to read/write persistent disk cache.
            
        Returns:
            2D numpy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        results: List[Optional[np.ndarray]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        if use_cache:
            for idx, text in enumerate(texts):
                h = self._compute_hash(text)
                cache_file = self.cache_dir / f"{h}.pkl"
                if cache_file.exists():
                    try:
                        with open(cache_file, "rb") as f:
                            results[idx] = pickle.load(f)
                    except Exception:
                        uncached_indices.append(idx)
                        uncached_texts.append(text)
                else:
                    uncached_indices.append(idx)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Encode uncached items in batches
        if uncached_texts:
            logger.info(f"Computing embeddings for {len(uncached_texts)} chunks (cached: {len(texts) - len(uncached_texts)})...")
            computed = self.model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=show_progress,
                device=self.device,
            )

            for i, orig_idx in enumerate(uncached_indices):
                emb = np.asarray(computed[i], dtype=np.float32)
                results[orig_idx] = emb
                if use_cache:
                    h = self._compute_hash(uncached_texts[i])
                    cache_file = self.cache_dir / f"{h}.pkl"
                    try:
                        with open(cache_file, "wb") as f:
                            pickle.dump(emb, f)
                    except Exception as e:
                        logger.warning(f"Failed to cache embedding: {e}")

        return np.vstack(results)

    def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = True,
        use_cache: bool = True,
    ) -> np.ndarray:
        """Alias for embed_documents."""
        return self.embed_documents(texts, show_progress=show_progress, use_cache=use_cache)
