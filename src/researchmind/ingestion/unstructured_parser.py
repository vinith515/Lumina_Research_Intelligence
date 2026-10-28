"""Unstructured.io PDF partitioner and element extractor for ResearchMind."""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element

from researchmind.schemas.models import DocumentElement, ElementType
from researchmind.config import settings

logger = logging.getLogger(__name__)


class UnstructuredPDFParser:
    """PDF parser using Unstructured.io to extract structured document elements."""

    def __init__(
        self,
        strategy: Optional[str] = None,
        extract_tables: Optional[bool] = None,
        fallback_strategy: Optional[str] = None,
    ):
        self.strategy = strategy or settings.UNSTRUCTURED_STRATEGY
        self.extract_tables = extract_tables if extract_tables is not None else settings.EXTRACT_TABLES
        self.fallback_strategy = fallback_strategy or settings.FALLBACK_STRATEGY

    def parse(self, pdf_path: Path, paper_id: str) -> List[DocumentElement]:
        """Parse a research paper PDF into structured DocumentElement objects.
        
        Args:
            pdf_path: Path to the PDF file.
            paper_id: Unique identifier for the paper.
            
        Returns:
            List of DocumentElement objects.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Parsing PDF {pdf_path.name} (ID: {paper_id}) using strategy '{self.strategy}'...")

        raw_elements: List[Element] = []
        try:
            raw_elements = partition_pdf(
                filename=str(pdf_path),
                strategy=self.strategy,
                extract_images_in_pdf=False,
                infer_table_structure=self.extract_tables,
                include_page_breaks=True,
            )
        except Exception as e:
            logger.warning(
                f"Parsing failed with strategy '{self.strategy}' for {pdf_path.name}: {e}. "
                f"Attempting fallback strategy '{self.fallback_strategy}'..."
            )
            try:
                raw_elements = partition_pdf(
                    filename=str(pdf_path),
                    strategy=self.fallback_strategy,
                    extract_images_in_pdf=False,
                    infer_table_structure=False,
                    include_page_breaks=True,
                )
            except Exception as fallback_err:
                logger.error(f"Fallback parsing also failed for {pdf_path.name}: {fallback_err}")
                raise RuntimeError(f"Failed to parse PDF {pdf_path.name}: {fallback_err}") from fallback_err

        structured_elements: List[DocumentElement] = []
        current_page = 1

        for idx, elem in enumerate(raw_elements):
            text = str(elem.text).strip()
            if not text and elem.category != "PageBreak":
                continue

            elem_meta = elem.metadata.to_dict() if hasattr(elem, "metadata") and elem.metadata else {}
            page_num = elem_meta.get("page_number", current_page)
            if elem.category == "PageBreak":
                current_page = page_num + 1 if page_num else current_page + 1
                continue
            else:
                current_page = page_num

            # Map coordinates if present
            coords = elem_meta.get("coordinates")
            clean_coords = None
            if coords and isinstance(coords, dict):
                clean_coords = {
                    "points": coords.get("points"),
                    "system": str(coords.get("system", "")),
                    "layout_width": coords.get("layout_width"),
                    "layout_height": coords.get("layout_height"),
                }

            category_name = elem.category or ElementType.NARRATIVE_TEXT.value
            elem_id = f"{paper_id}_elem_{idx:04d}"

            # Extra metadata preservation
            extra_meta: Dict[str, Any] = {
                "filename": pdf_path.name,
                "element_index": idx,
                "unstructured_type": category_name,
            }
            if "table_as_html" in elem_meta:
                extra_meta["table_html"] = elem_meta["table_as_html"]
            if "languages" in elem_meta:
                extra_meta["languages"] = elem_meta["languages"]
            if "parent_id" in elem_meta:
                extra_meta["parent_id"] = elem_meta["parent_id"]

            doc_elem = DocumentElement(
                paper_id=paper_id,
                element_id=elem_id,
                element_type=category_name,
                text=text,
                page_number=current_page,
                coordinates=clean_coords,
                metadata=extra_meta,
            )
            structured_elements.append(doc_elem)

        logger.info(f"Extracted {len(structured_elements)} structured elements from {pdf_path.name}")
        return structured_elements
