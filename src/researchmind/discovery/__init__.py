"""Online research discovery module."""

from researchmind.discovery.base import ResearchSourceProvider, OnlinePaperCandidate
from researchmind.discovery.arxiv_provider import ArxivProvider
from researchmind.discovery.semantic_scholar_provider import SemanticScholarProvider
from researchmind.discovery.discovery_service import ResearchDiscoveryService

__all__ = [
    "ResearchSourceProvider",
    "OnlinePaperCandidate",
    "ArxivProvider",
    "SemanticScholarProvider",
    "ResearchDiscoveryService",
]
