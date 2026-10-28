"""Modular chunking strategies protocol and alternative implementations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from researchmind.schemas.models import DocumentElement, ResearchChunk, PaperMetadata
from researchmind.chunking.research_chunker import ResearchPaperChunker


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(
        self,
        paper_id: str,
        elements: List[DocumentElement],
        metadata: Optional[PaperMetadata] = None,
    ) -> List[ResearchChunk]:
        """Convert elements into chunks."""
        pass


class ResearchAwareChunkingStrategy(ChunkingStrategy):
    """Default structure- and section-aware chunking strategy."""

    def __init__(
        self,
        target_size: Optional[int] = None,
        max_size: Optional[int] = None,
        min_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ):
        self.chunker = ResearchPaperChunker(
            target_size=target_size,
            max_size=max_size,
            min_size=min_size,
            overlap=overlap,
        )

    def chunk(
        self,
        paper_id: str,
        elements: List[DocumentElement],
        metadata: Optional[PaperMetadata] = None,
    ) -> List[ResearchChunk]:
        return self.chunker.chunk_paper(paper_id, elements, metadata)


class FixedSizeChunkingStrategy(ChunkingStrategy):
    """Baseline fixed character/token chunking strategy for experimental comparison."""

    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        paper_id: str,
        elements: List[DocumentElement],
        metadata: Optional[PaperMetadata] = None,
    ) -> List[ResearchChunk]:
        full_text = "\n\n".join(e.text for e in elements if e.text.strip())
        chunks: List[ResearchChunk] = []
        step = max(100, self.chunk_size - self.overlap)
        
        title = metadata.title if metadata else ""
        authors = metadata.authors if metadata else []

        idx = 0
        for start in range(0, len(full_text), step):
            sub_text = full_text[start:start + self.chunk_size].strip()
            if len(sub_text) < 50:
                continue
            chunk_id = f"{paper_id}_fix_{idx:03d}"
            chunks.append(
                ResearchChunk(
                    chunk_id=chunk_id,
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    section="Fixed Chunk",
                    page_start=1,
                    page_end=1,
                    text=sub_text,
                    chunk_index=idx,
                    token_count=len(sub_text.split()),
                    char_count=len(sub_text),
                )
            )
            idx += 1

        return chunks
