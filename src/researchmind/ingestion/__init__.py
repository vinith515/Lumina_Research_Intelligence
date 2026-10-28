"""Ingestion module using Unstructured.io."""

from researchmind.ingestion.unstructured_parser import UnstructuredPDFParser
from researchmind.ingestion.cleaner import DocumentCleaner
from researchmind.ingestion.metadata import AcademicMetadataExtractor
from researchmind.ingestion.pipeline import IngestionPipeline

__all__ = [
    "UnstructuredPDFParser",
    "DocumentCleaner",
    "AcademicMetadataExtractor",
    "IngestionPipeline",
]
