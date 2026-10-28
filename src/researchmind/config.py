"""Configuration management for ResearchMind using Pydantic Settings."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Eagerly load environment variables from .env if present
load_dotenv()


class Settings(BaseSettings):
    """Centralized ResearchMind configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RESEARCHMIND_",
        extra="ignore",
    )

    # Base Paths
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(os.getcwd()).resolve())
    DATA_DIR: str = "AI_Research_Dataset"
    PROCESSED_DIR: str = "data/processed"
    METADATA_DIR: str = "data/metadata"
    INDEX_DIR: str = "indexes"
    EXPERIMENTS_DIR: str = "experiments"

    # Ingestion Settings
    UNSTRUCTURED_STRATEGY: str = "fast"  # 'fast', 'auto', 'hi_res'
    FALLBACK_STRATEGY: str = "auto"
    EXTRACT_TABLES: bool = True
    MAX_FILE_SIZE_MB: float = 100.0

    # Document Cleaner Settings
    STRIP_REPEATED_HEADERS: bool = True
    STRIP_REPEATED_FOOTERS: bool = True
    NORMALIZE_WHITESPACE: bool = True
    FIX_LINE_WRAPPING: bool = True

    # Research Chunker Settings
    TARGET_CHUNK_SIZE: int = 1800   # in characters (~450 tokens)
    MAX_CHUNK_SIZE: int = 3000      # in characters (~750 tokens)
    MIN_CHUNK_SIZE: int = 150       # in characters
    CHUNK_OVERLAP: int = 200        # in characters

    # Embedding Settings
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    DEVICE: str = "cuda"  # 'cuda' or 'cpu'
    EMBEDDING_BATCH_SIZE: int = 32
    NORMALIZE_EMBEDDINGS: bool = True
    CACHE_EMBEDDINGS: bool = True

    # Retrieval Settings
    DENSE_TOP_K: int = 20
    SPARSE_TOP_K: int = 20
    RRF_K: int = 60
    HYBRID_TOP_K: int = 20

    # Reranking Settings
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 5
    ENABLE_RERANKER: bool = True

    # Generation & LLM Settings
    LLM_PROVIDER: str = "gemini"  # 'gemini', 'openai', 'anthropic', 'ollama'
    LLM_MODEL: str = "gemini-3.6-flash"
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 2048

    # API Keys (read from environment directly if not prefixed)
    GEMINI_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("RESEARCHMIND_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))
    OPENAI_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("RESEARCHMIND_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    ANTHROPIC_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("RESEARCHMIND_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    OLLAMA_BASE_URL: str = Field(default_factory=lambda: os.getenv("RESEARCHMIND_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    # Explainable AI (XAI)
    ENABLE_XAI: bool = True
    MIN_EVIDENCE_SCORE: float = 0.3
    GROUNDING_SIMILARITY_THRESHOLD: float = 0.55
    EVIDENCE_SUFFICIENCY_THRESHOLD: float = 0.35

    # Dynamic Ingestion & User Upload Paths
    USER_UPLOAD_DIR: str = "data/user_uploads"
    ONLINE_PAPERS_DIR: str = "data/online_papers"

    # Online Research Discovery
    ONLINE_SEARCH_LIMIT: int = 5
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("RESEARCHMIND_SEMANTIC_SCHOLAR_API_KEY") or os.getenv("SEMANTIC_SCHOLAR_API_KEY"))

    # Celery & Redis Task Queue
    REDIS_URL: str = Field(default_factory=lambda: os.getenv("RESEARCHMIND_REDIS_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_BROKER_URL: str = Field(default_factory=lambda: os.getenv("RESEARCHMIND_CELERY_BROKER_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = Field(default_factory=lambda: os.getenv("RESEARCHMIND_CELERY_RESULT_BACKEND") or os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))

    @property
    def raw_data_path(self) -> Path:
        p = Path(self.DATA_DIR)
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def elements_dir(self) -> Path:
        p = Path(self.PROCESSED_DIR) / "elements"
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def chunks_dir(self) -> Path:
        p = Path(self.PROCESSED_DIR) / "chunks"
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def metadata_path(self) -> Path:
        p = Path(self.METADATA_DIR)
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def vector_index_path(self) -> Path:
        p = Path(self.INDEX_DIR) / "vector"
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def bm25_index_path(self) -> Path:
        p = Path(self.INDEX_DIR) / "bm25"
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def experiments_path(self) -> Path:
        p = Path(self.EXPERIMENTS_DIR)
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def user_upload_path(self) -> Path:
        p = Path(self.USER_UPLOAD_DIR)
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    @property
    def online_papers_path(self) -> Path:
        p = Path(self.ONLINE_PAPERS_DIR)
        return p if p.is_absolute() else self.PROJECT_ROOT / p

    def ensure_directories(self) -> None:
        """Ensure all required output and cache directories exist."""
        self.elements_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        self.vector_index_path.mkdir(parents=True, exist_ok=True)
        self.bm25_index_path.mkdir(parents=True, exist_ok=True)
        self.experiments_path.mkdir(parents=True, exist_ok=True)
        self.user_upload_path.mkdir(parents=True, exist_ok=True)
        self.online_papers_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
