"""Document cleaning and normalization for extracted structured elements."""

import re
import logging
from collections import Counter
from typing import List, Dict, Set
from researchmind.schemas.models import DocumentElement, ElementType
from researchmind.config import settings

logger = logging.getLogger(__name__)


class DocumentCleaner:
    """Cleans and normalizes structured elements extracted from research papers."""

    def __init__(
        self,
        strip_headers: bool = True,
        strip_footers: bool = True,
        normalize_whitespace: bool = True,
        fix_line_wrapping: bool = True,
    ):
        self.strip_headers = strip_headers
        self.strip_footers = strip_footers
        self.normalize_whitespace = normalize_whitespace
        self.fix_line_wrapping = fix_line_wrapping

        # Patterns for standalone page numbers (e.g., "1", "Page 12", "12 | Journal Name")
        self.page_number_pattern = re.compile(r"^(?:page\s*)?\d{1,4}(?:\s*of\s*\d{1,4})?$", re.IGNORECASE)
        # Hyphenation at line break (e.g., "distil-\nlation" -> "distillation")
        self.hyphen_break_pattern = re.compile(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)")
        # Multiple newline reduction
        self.multi_newline_pattern = re.compile(r"\n{3,}")
        # Multiple space reduction
        self.multi_space_pattern = re.compile(r"[ \t]{2,}")

    def clean_elements(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """Clean a list of DocumentElements from a single paper.
        
        Args:
            elements: Raw extracted DocumentElement list.
            
        Returns:
            Cleaned and normalized DocumentElement list.
        """
        if not elements:
            return []

        # Step 1: Detect repetitive running headers and footers across pages
        repetitive_texts = self._detect_repetitive_patterns(elements)

        cleaned: List[DocumentElement] = []
        for elem in elements:
            raw_text = elem.text.strip()
            if not raw_text:
                continue

            # Check if this element is a standalone page number
            if self.page_number_pattern.match(raw_text):
                continue

            # Check if marked as Header/Footer and is repetitive across pages
            if elem.element_type in [ElementType.HEADER.value, ElementType.FOOTER.value, "Header", "Footer"]:
                if raw_text in repetitive_texts or len(raw_text) < 50:
                    continue

            # Check if text is repetitive across >= 3 distinct pages
            if raw_text in repetitive_texts and len(raw_text) < 120:
                continue

            # Normalize text content
            cleaned_text = self.clean_text(raw_text)
            if not cleaned_text:
                continue

            # Create updated element copy
            cleaned_elem = DocumentElement(
                paper_id=elem.paper_id,
                element_id=elem.element_id,
                element_type=elem.element_type,
                text=cleaned_text,
                page_number=elem.page_number,
                coordinates=elem.coordinates,
                metadata=elem.metadata,
            )
            cleaned.append(cleaned_elem)

        logger.debug(f"Cleaned {len(elements)} raw elements down to {len(cleaned)} normalized elements.")
        return cleaned

    def clean_text(self, text: str) -> str:
        """Clean and normalize a single text string preserving technical content."""
        if not text:
            return ""

        # 1. Remove non-printable control characters (except tab, newline)
        text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")

        # 2. Fix hyphenated line wraps (e.g. 'compo-\nnent' -> 'component')
        if self.fix_line_wrapping:
            text = self.hyphen_break_pattern.sub(r"\1\2", text)

        # 3. Replace irregular whitespace and tabs
        if self.normalize_whitespace:
            text = self.multi_space_pattern.sub(" ", text)
            text = self.multi_newline_pattern.sub("\n\n", text)

        # 4. Strip surrounding whitespace
        return text.strip()

    def _detect_repetitive_patterns(self, elements: List[DocumentElement]) -> Set[str]:
        """Detect lines/headers that repeat across multiple pages (e.g. journal title, footer)."""
        page_occurrences: Dict[str, Set[int]] = {}
        for elem in elements:
            t = elem.text.strip()
            if 5 < len(t) < 150:
                if t not in page_occurrences:
                    page_occurrences[t] = set()
                page_occurrences[t].add(elem.page_number)

        # Repetitive if it appears on 3 or more distinct pages
        repetitive = {t for t, pages in page_occurrences.items() if len(pages) >= 3}
        return repetitive
