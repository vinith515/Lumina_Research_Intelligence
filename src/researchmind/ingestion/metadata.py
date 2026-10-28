"""Metadata extraction and academic document structure analysis."""

import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from researchmind.schemas.models import DocumentElement, PaperMetadata, ElementType

logger = logging.getLogger(__name__)


class AcademicMetadataExtractor:
    """Extracts paper-level metadata (title, authors, abstract, sections) and assigns section hierarchy to elements."""

    # Regex patterns for section titles (e.g., "1. Introduction", "2.1 Problem Formulation", "IV. RESULTS", "Abstract")
    SECTION_PATTERNS = [
        re.compile(r"^(?:[0-9]{1,2}(?:\.[0-9]{1,2}){0,2})\s+([A-Z][a-zA-Z0-9\s\-:,]{2,60})$"),
        re.compile(r"^(?:[I|V|X]{1,4}\.)\s+([A-Z\s\-:,]{2,60})$"),
        re.compile(r"^(?:SECTION\s+[0-9IVX]+[:\.]?)\s*(.*)$", re.IGNORECASE),
        re.compile(r"^(Abstract|Introduction|Related Work|Background|Methodology|Methods|Method|Architecture|Proposed Method|Experiments|Experimental Setup|Results|Discussion|Conclusion|Conclusions|References|Acknowledgments|Ablation Study)$", re.IGNORECASE),
    ]

    # Regex for DOI
    DOI_PATTERN = re.compile(r"(?:10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
    # Regex for Year
    YEAR_PATTERN = re.compile(r"\b(20[0-2][0-9]|19[89][0-9])\b")
    # Regex for arXiv ID
    ARXIV_PATTERN = re.compile(r"arxiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", re.IGNORECASE)

    def extract_paper_metadata(
        self,
        pdf_path: Path,
        paper_id: str,
        file_hash: str,
        elements: List[DocumentElement],
        category: str = "General",
    ) -> Tuple[PaperMetadata, List[DocumentElement]]:
        """Extract paper title, authors, abstract, and assign section hierarchy to all elements.
        
        Args:
            pdf_path: Path to PDF.
            paper_id: Unique paper ID.
            file_hash: SHA-256 hash of PDF.
            elements: Cleaned DocumentElements.
            category: Domain category (e.g. ComputerVision, NLP).
            
        Returns:
            Tuple of (PaperMetadata, enriched DocumentElements with section metadata).
        """
        title = self._infer_title(pdf_path, elements)
        authors = self._infer_authors(elements, title)
        abstract = self._infer_abstract(elements)
        doi, year = self._infer_publication_info(elements)

        # Tag elements with active section & subsection hierarchy
        enriched_elements = self._assign_section_hierarchy(elements)

        total_pages = max((e.page_number for e in elements), default=1)

        metadata = PaperMetadata(
            paper_id=paper_id,
            filename=pdf_path.name,
            file_path=str(pdf_path),
            file_hash=file_hash,
            category=category,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            total_pages=total_pages,
            total_elements=len(enriched_elements),
            status="processed",
        )

        return metadata, enriched_elements

    def _infer_title(self, pdf_path: Path, elements: List[DocumentElement]) -> str:
        """Infer paper title from Title elements or top text on page 1, or fallback to cleaned filename."""
        page1_elements = [e for e in elements if e.page_number == 1]
        
        # 1. Look for explicit Title elements on page 1 (ignoring arXiv headers or metadata)
        for e in page1_elements[:8]:
            t = e.text.strip()
            if len(t) < 10 or len(t) > 300:
                continue
            if any(k in t.lower() for k in ["arxiv:", "ieee", "springer", "proceedings", "conference", "preprint", "volume xx"]):
                continue
            if e.element_type in [ElementType.TITLE.value, "Title"]:
                return t

        # 2. Look for the first prominent narrative text block on page 1 that is not an arXiv banner
        for e in page1_elements[:6]:
            t = e.text.strip()
            if 15 < len(t) < 250 and not t.lower().startswith("abstract") and not "arxiv:" in t.lower():
                if not any(k in t.lower() for k in ["university", "department", "institute", "laboratory", "@"]):
                    return t

        # 3. Fallback: cleaned filename
        clean_name = pdf_path.stem.replace("_", " ").replace("-", " ")
        return clean_name

    def _infer_authors(self, elements: List[DocumentElement], title: str) -> List[str]:
        """Infer authors if reliably present near top of page 1."""
        page1_elements = [e for e in elements if e.page_number == 1]
        authors: List[str] = []

        title_seen = False
        for e in page1_elements[:10]:
            t = e.text.strip()
            if "arxiv:" in t.lower():
                continue
            if t == title or title in t:
                title_seen = True
                continue
            if t.lower().startswith("abstract"):
                break
            if not title_seen:
                continue

            # Candidate author line
            if any(k in t.lower() for k in ["university", "department", "institute", "laboratory", "@", "email"]):
                continue
            if 4 < len(t) < 180:
                # Remove superscript numbers often appended to authors (e.g. Ren1, Liu1 -> Ren, Liu)
                t_clean = re.sub(r"[\d\*\†\‡]+", "", t).strip()
                split_authors = [a.strip() for a in re.split(r",|\band\b", t_clean) if a.strip()]
                if 1 <= len(split_authors) <= 10:
                    authors = split_authors
                    break

        return authors

    def _infer_abstract(self, elements: List[DocumentElement]) -> Optional[str]:
        """Extract abstract text if present in document elements."""
        for idx, e in enumerate(elements[:15]):
            t = e.text.strip()
            # If element text starts with 'Abstract'
            if re.match(r"^abstract[\s:\.\-—]*", t, re.IGNORECASE):
                # Strip prefix
                abstract_body = re.sub(r"^abstract[\s:\.\-—]*", "", t, flags=re.IGNORECASE).strip()
                if len(abstract_body) > 40:
                    return abstract_body
                # If abstract header was separate, next element might be abstract text
                if idx + 1 < len(elements):
                    next_text = elements[idx + 1].text.strip()
                    if len(next_text) > 60:
                        return next_text

        return None

    def _infer_publication_info(self, elements: List[DocumentElement]) -> Tuple[Optional[str], Optional[int]]:
        """Extract DOI and Publication Year if present."""
        doi: Optional[str] = None
        year: Optional[int] = None

        full_sample = " ".join([e.text for e in elements[:10]] + [e.text for e in elements[-5:]])
        
        doi_match = self.DOI_PATTERN.search(full_sample)
        if doi_match:
            doi = doi_match.group(0)

        year_match = self.YEAR_PATTERN.findall(full_sample)
        if year_match:
            # Pick reasonable recent year
            years = [int(y) for y in year_match if 1990 <= int(y) <= 2026]
            if years:
                year = max(years)

        return doi, year

    def _assign_section_hierarchy(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """Assign section and subsection hierarchy to each element based on heading detection."""
        current_section = "Introduction / Header"
        current_subsection: Optional[str] = None

        enriched: List[DocumentElement] = []
        for elem in elements:
            text = elem.text.strip()
            is_heading = False

            # Check if element is an Unstructured Title or matches a section regex
            if elem.element_type in [ElementType.TITLE.value, ElementType.SECTION_HEADER.value, "Title"]:
                if len(text) < 100:
                    is_heading = True

            if not is_heading:
                for pattern in self.SECTION_PATTERNS:
                    if pattern.match(text):
                        is_heading = True
                        break

            if is_heading and len(text) < 100:
                # Check if subsection (e.g. 3.2, 4.1.1) or top-level section
                if re.match(r"^\d+\.\d+", text):
                    current_subsection = text
                else:
                    current_section = text
                    current_subsection = None

            # Attach section metadata to the element
            meta = dict(elem.metadata)
            meta["section"] = current_section
            if current_subsection:
                meta["subsection"] = current_subsection

            updated_elem = DocumentElement(
                paper_id=elem.paper_id,
                element_id=elem.element_id,
                element_type=elem.element_type,
                text=elem.text,
                page_number=elem.page_number,
                coordinates=elem.coordinates,
                metadata=meta,
            )
            enriched.append(updated_elem)

        return enriched
