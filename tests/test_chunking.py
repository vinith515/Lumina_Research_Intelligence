"""Unit tests for Research-Paper-Aware chunking."""

from researchmind.schemas.models import DocumentElement, PaperMetadata
from researchmind.chunking.research_chunker import ResearchPaperChunker
from researchmind.chunking.strategies import ResearchAwareChunkingStrategy, FixedSizeChunkingStrategy


def test_research_chunker_preserves_sections(sample_elements):
    chunker = ResearchPaperChunker(target_size=200, min_size=50)
    meta = PaperMetadata(
        paper_id="test_paper_001",
        filename="test.pdf",
        file_path="test.pdf",
        file_hash="abc12345",
        title="ADOPD: Test Paper",
        authors=["Alice Smith"],
    )

    chunks = chunker.chunk_paper("test_paper_001", sample_elements, metadata=meta)
    assert len(chunks) >= 2

    # Verify sections are preserved
    sections = [c.section for c in chunks]
    assert "Introduction" in sections
    assert "3. Methodology" in sections

    # Verify chunk attributes
    for c in chunks:
        assert c.paper_id == "test_paper_001"
        assert c.title == "ADOPD: Test Paper"
        assert c.token_count > 0
        assert c.char_count > 0
        assert c.page_start >= 1


def test_fixed_size_strategy(sample_elements):
    strategy = FixedSizeChunkingStrategy(chunk_size=100, overlap=20)
    chunks = strategy.chunk("test_paper_001", sample_elements)
    assert len(chunks) >= 1
    assert chunks[0].chunk_id.startswith("test_paper_001_fix_")
