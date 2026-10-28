"""Research-paper-aware chunking engine preserving section boundaries and semantic units."""

import logging
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from researchmind.schemas.models import DocumentElement, ResearchChunk, PaperMetadata, ElementType
from researchmind.config import settings

logger = logging.getLogger(__name__)


class ResearchPaperChunker:
    """Structure-aware chunking engine tailored for scientific research papers."""

    def __init__(
        self,
        target_size: Optional[int] = None,
        max_size: Optional[int] = None,
        min_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ):
        self.target_size = target_size or settings.TARGET_CHUNK_SIZE
        self.max_size = max_size or settings.MAX_CHUNK_SIZE
        self.min_size = min_size or settings.MIN_CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP

    def chunk_paper(
        self,
        paper_id: str,
        elements: List[DocumentElement],
        metadata: Optional[PaperMetadata] = None,
    ) -> List[ResearchChunk]:
        """Chunk cleaned document elements of a single paper respecting section hierarchy and logical units.
        
        Args:
            paper_id: Unique paper ID.
            elements: Cleaned and section-enriched DocumentElements.
            metadata: Optional PaperMetadata for attaching title and authors.
            
        Returns:
            List of ResearchChunk objects.
        """
        if not elements:
            return []

        title = metadata.title if metadata else elements[0].metadata.get("title", "")
        authors = metadata.authors if metadata else elements[0].metadata.get("authors", [])

        # Step 1: Group elements by primary section
        section_groups = self._group_by_section(elements)

        chunks: List[ResearchChunk] = []
        chunk_counter = 0

        for section_name, section_elements in section_groups.items():
            if not section_elements:
                continue

            # Step 2: Split section into coherent chunks bounded by size and logical flow
            section_chunks = self._chunk_section(
                paper_id=paper_id,
                title=title,
                authors=authors,
                section_name=section_name,
                elements=section_elements,
                start_index=chunk_counter,
                metadata=metadata,
            )
            chunks.extend(section_chunks)
            chunk_counter += len(section_chunks)

        logger.debug(f"Generated {len(chunks)} research chunks for paper {paper_id}")
        return chunks

    def _group_by_section(self, elements: List[DocumentElement]) -> Dict[str, List[DocumentElement]]:
        """Group elements by their detected section name to prevent cross-section bleeding."""
        groups: Dict[str, List[DocumentElement]] = {}
        for elem in elements:
            sec = elem.metadata.get("section", "General")
            if sec not in groups:
                groups[sec] = []
            groups[sec].append(elem)
        return groups

    def _chunk_section(
        self,
        paper_id: str,
        title: str,
        authors: List[str],
        section_name: str,
        elements: List[DocumentElement],
        start_index: int,
        metadata: Optional[PaperMetadata] = None,
    ) -> List[ResearchChunk]:
        """Build chunks within a single section."""
        scope = getattr(metadata, "scope", "global") if metadata else "global"
        session_id = getattr(metadata, "session_id", None) if metadata else None
        source = getattr(metadata, "source", "corpus") if metadata else "corpus"

        chunks: List[ResearchChunk] = []
        current_texts: List[str] = []
        current_element_types: List[str] = []
        current_pages: List[int] = []
        current_subsections: List[str] = []
        current_coordinates: List[Any] = []
        current_len = 0

        def flush_chunk():
            nonlocal current_texts, current_element_types, current_pages, current_subsections, current_coordinates, current_len
            if not current_texts:
                return

            combined_text = "\n\n".join(current_texts).strip()
            if len(combined_text) < self.min_size and chunks:
                # If chunk is too small, merge with previous chunk if within max_size
                prev = chunks[-1]
                if len(prev.text) + len(combined_text) + 2 <= self.max_size:
                    prev.text = prev.text + "\n\n" + combined_text
                    prev.page_end = max(prev.page_end, max(current_pages))
                    prev.char_count = len(prev.text)
                    prev.token_count = len(prev.text.split())
                    prev.element_types = list(set(prev.element_types + current_element_types))
                    if current_coordinates and prev.bbox:
                        prev.bbox.extend(current_coordinates)
                    elif current_coordinates and not prev.bbox:
                        prev.bbox = list(current_coordinates)
                    current_texts, current_element_types, current_pages, current_subsections, current_coordinates, current_len = [], [], [], [], [], 0
                    return

            idx = start_index + len(chunks)
            chunk_id = f"{paper_id}_chk_{idx:03d}"
            primary_sub = current_subsections[0] if current_subsections else None

            # Calculate approximate token count (~1.3 tokens per word or chars/4)
            approx_tokens = len(combined_text.split())

            new_chunk = ResearchChunk(
                chunk_id=chunk_id,
                paper_id=paper_id,
                title=title,
                authors=authors,
                section=section_name,
                subsection=primary_sub,
                page_start=min(current_pages) if current_pages else 1,
                page_end=max(current_pages) if current_pages else 1,
                element_types=list(set(current_element_types)),
                text=combined_text,
                chunk_index=idx,
                token_count=approx_tokens,
                char_count=len(combined_text),
                scope=scope,
                session_id=session_id,
                source=source,
                bbox=list(current_coordinates) if current_coordinates else None,
                metadata={
                    "section": section_name,
                    "subsection": primary_sub,
                    "page_range": f"{min(current_pages) if current_pages else 1}-{max(current_pages) if current_pages else 1}",
                    "scope": scope,
                    "source": source,
                }
            )
            chunks.append(new_chunk)

            # Support overlap: carry forward the last paragraph if overlap is configured
            if self.overlap > 0 and len(current_texts) > 1 and len(current_texts[-1]) < self.overlap:
                last_text = current_texts[-1]
                last_type = current_element_types[-1]
                last_page = current_pages[-1]
                last_coords = [current_coordinates[-1]] if current_coordinates else []
                current_texts = [last_text]
                current_element_types = [last_type]
                current_pages = [last_page]
                current_coordinates = last_coords
                current_len = len(last_text)
            else:
                current_texts = []
                current_element_types = []
                current_pages = []
                current_subsections = []
                current_coordinates = []
                current_len = 0

        for elem in elements:
            elem_text = elem.text.strip()
            if not elem_text:
                continue

            elem_len = len(elem_text)
            elem_type = elem.element_type
            sub = elem.metadata.get("subsection")

            # Check if adding this element exceeds target size and current_len > 0
            if (current_len + elem_len > self.target_size and current_len >= self.min_size) or (current_len + elem_len > self.max_size):
                flush_chunk()

            current_texts.append(elem_text)
            current_element_types.append(elem_type)
            current_pages.append(elem.page_number)
            if elem.coordinates:
                current_coordinates.append(elem.coordinates)
            if sub and sub not in current_subsections:
                current_subsections.append(sub)
            current_len += elem_len

        # Flush any remaining text in the section
        if current_texts:
            flush_chunk()

        return chunks
