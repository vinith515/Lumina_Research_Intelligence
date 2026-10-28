"""Modular Online Research Discovery provider interface and candidate models."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
import re
from pydantic import BaseModel, Field, model_validator


def extract_academic_search_keywords(query: str) -> str:
    """Extract informative academic keywords from natural language research questions or queries.
    
    Transforms questions like 'What are the best defense mechanisms against adversarial attacks in computer vision?'
    into focused academic search terms like 'defense mechanisms adversarial attacks computer vision'.
    """
    if not query:
        return ""
        
    clean = re.sub(r"[^\w\s-]", " ", query).strip()
    words = clean.split()
    if not words:
        return query.strip()

    STOP_WORDS = {
        "what", "is", "are", "was", "were", "be", "been", "being",
        "how", "why", "when", "where", "who", "whom", "which",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "by", "about", "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "out", "off", "over", "under",
        "can", "could", "would", "should", "shall", "will", "do", "does", "did",
        "have", "has", "had", "having", "may", "might", "must",
        "find", "search", "give", "show", "tell", "explain", "describe", "list",
        "paper", "papers", "article", "articles", "research", "study", "studies", "literature",
        "recent", "latest", "new", "best", "current", "state", "art",
        "please", "help", "me", "you", "i", "we", "our", "their", "it", "its", "this", "that", "these", "those",
    }

    filtered = [w for w in words if w.lower() not in STOP_WORDS]
    if not filtered:
        return " ".join(words)
    return " ".join(filtered)


class OnlinePaperCandidate(BaseModel):
    """Normalized candidate paper discovered from external academic repositories."""
    candidate_id: str
    id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    source: str = "arxiv"  # 'arxiv', 'semantic_scholar'
    source_provider: Optional[str] = None
    identifier: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    paper_url: Optional[str] = None
    pdf_url: Optional[str] = None
    relevance_score: float = 0.0
    rank: int = 1
    already_exists_locally: bool = False
    existing_paper_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_id_and_provider_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "candidate_id" not in data and "id" in data:
                data["candidate_id"] = data["id"]
            elif "id" not in data and "candidate_id" in data:
                data["id"] = data["candidate_id"]

            if "source" not in data and "source_provider" in data:
                data["source"] = data["source_provider"]
            elif "source_provider" not in data and "source" in data:
                data["source_provider"] = data["source"]
        return data

    @model_validator(mode="after")
    def sync_id_and_provider_after(self) -> "OnlinePaperCandidate":
        if not self.id and self.candidate_id:
            self.id = self.candidate_id
        if not self.candidate_id and self.id:
            self.candidate_id = self.id
        if not self.source_provider and self.source:
            self.source_provider = self.source
        if not self.source and self.source_provider:
            self.source = self.source_provider
        return self


class ResearchSourceProvider(ABC):
    """Abstract interface for external scientific paper search providers."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[OnlinePaperCandidate]:
        """Search the external provider for research papers matching the query."""
        pass

    @abstractmethod
    def get_paper_metadata(self, identifier: str) -> Optional[OnlinePaperCandidate]:
        """Fetch metadata for a single specific manuscript by ID."""
        pass

    @abstractmethod
    def download_pdf(self, candidate: OnlinePaperCandidate, target_path: Path) -> Path:
        """Download manuscript PDF to the specified destination path."""
        pass

    @abstractmethod
    def supports_pdf(self, candidate: OnlinePaperCandidate) -> bool:
        """Check whether direct PDF download is supported for this candidate."""
        pass
