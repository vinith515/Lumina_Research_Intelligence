"""Pytest fixtures for ResearchMind."""

import sys
from pathlib import Path
import pytest
import numpy as np

# Ensure src is in python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from researchmind.schemas.models import (
    DocumentElement,
    PaperMetadata,
    ResearchChunk,
    RetrievalCandidate,
)


@pytest.fixture
def sample_elements():
    """Mock DocumentElement list representing a research paper."""
    return [
        DocumentElement(
            paper_id="test_paper_001",
            element_id="test_paper_001_elem_0001",
            element_type="Title",
            text="ADOPD: Reference-Privileged On-Policy Distillation for MLLM Anomaly Detection",
            page_number=1,
            metadata={"section": "Introduction"},
        ),
        DocumentElement(
            paper_id="test_paper_001",
            element_id="test_paper_001_elem_0002",
            element_type="NarrativeText",
            text="Abstract: Multimodal Large Language Models (MLLMs) have shown remarkable capabilities in anomaly detection.",
            page_number=1,
            metadata={"section": "Introduction"},
        ),
        DocumentElement(
            paper_id="test_paper_001",
            element_id="test_paper_001_elem_0003",
            element_type="Title",
            text="3. Methodology",
            page_number=3,
            metadata={"section": "3. Methodology"},
        ),
        DocumentElement(
            paper_id="test_paper_001",
            element_id="test_paper_001_elem_0004",
            element_type="NarrativeText",
            text="We propose an on-policy distillation framework that leverages reference images during training but operates reference-free at inference.",
            page_number=3,
            metadata={"section": "3. Methodology", "subsection": "3.1 Formulation"},
        ),
        DocumentElement(
            paper_id="test_paper_001",
            element_id="test_paper_001_elem_0005",
            element_type="NarrativeText",
            text="The loss function combines cross-entropy with a distillation divergence term to align teacher and student predictions.",
            page_number=4,
            metadata={"section": "3. Methodology", "subsection": "3.2 Loss Function"},
        ),
    ]


@pytest.fixture
def sample_chunks():
    """Mock ResearchChunk list."""
    return [
        ResearchChunk(
            chunk_id="test_paper_001_chk_000",
            paper_id="test_paper_001",
            title="ADOPD: Reference-Privileged On-Policy Distillation",
            authors=["Alice Smith", "Bob Jones"],
            section="Introduction",
            page_start=1,
            page_end=1,
            element_types=["Title", "NarrativeText"],
            text="Multimodal Large Language Models (MLLMs) have shown remarkable capabilities in industrial anomaly detection tasks.",
            chunk_index=0,
            token_count=18,
            char_count=115,
        ),
        ResearchChunk(
            chunk_id="test_paper_001_chk_001",
            paper_id="test_paper_001",
            title="ADOPD: Reference-Privileged On-Policy Distillation",
            authors=["Alice Smith", "Bob Jones"],
            section="3. Methodology",
            subsection="3.1 Formulation",
            page_start=3,
            page_end=4,
            element_types=["NarrativeText"],
            text="We propose an on-policy distillation framework that leverages reference images during training but operates reference-free at inference.",
            chunk_index=1,
            token_count=21,
            char_count=138,
        ),
    ]
