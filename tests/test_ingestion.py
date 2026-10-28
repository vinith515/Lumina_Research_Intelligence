"""Unit tests for Cleaner and Academic Metadata Extractor."""

from pathlib import Path
from researchmind.schemas.models import DocumentElement, ElementType
from researchmind.ingestion.cleaner import DocumentCleaner
from researchmind.ingestion.metadata import AcademicMetadataExtractor


def test_document_cleaner():
    cleaner = DocumentCleaner(strip_headers=True, strip_footers=True, normalize_whitespace=True)
    elements = [
        DocumentElement(paper_id="p1", element_id="e1", element_type="Header", text="IEEE Transactions on AI", page_number=1),
        DocumentElement(paper_id="p1", element_id="e2", element_type="NarrativeText", text="This is   some text with   excessive  spaces.\n\n\nAnd newlines.", page_number=1),
        DocumentElement(paper_id="p1", element_id="e3", element_type="Header", text="IEEE Transactions on AI", page_number=2),
        DocumentElement(paper_id="p1", element_id="e4", element_type="Header", text="IEEE Transactions on AI", page_number=3),
        DocumentElement(paper_id="p1", element_id="e5", element_type="Text", text="12", page_number=3),  # standalone page number
    ]

    cleaned = cleaner.clean_elements(elements)
    assert len(cleaned) == 1
    assert "This is some text with excessive spaces." in cleaned[0].text


def test_metadata_extractor():
    extractor = AcademicMetadataExtractor()
    elements = [
        DocumentElement(paper_id="p1", element_id="e1", element_type="Title", text="Deep Graph Neural Networks for Anomaly Diagnosis", page_number=1),
        DocumentElement(paper_id="p1", element_id="e2", element_type="Text", text="John Doe, Jane Smith", page_number=1),
        DocumentElement(paper_id="p1", element_id="e3", element_type="NarrativeText", text="Abstract: This paper presents an explainable graph neural network...", page_number=1),
        DocumentElement(paper_id="p1", element_id="e4", element_type="Title", text="1. Introduction", page_number=1),
        DocumentElement(paper_id="p1", element_id="e5", element_type="NarrativeText", text="Graph neural networks have become popular.", page_number=1),
    ]

    meta, enriched = extractor.extract_paper_metadata(
        pdf_path=Path("Deep_Graph.pdf"),
        paper_id="p1",
        file_hash="hash123",
        elements=elements,
        category="DeepLearning",
    )

    assert meta.title == "Deep Graph Neural Networks for Anomaly Diagnosis"
    assert "John Doe" in meta.authors
    assert meta.abstract is not None
    assert "explainable graph neural network" in meta.abstract
    assert enriched[4].metadata.get("section") == "1. Introduction"
