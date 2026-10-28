"""Comprehensive unit and integration tests for context-aware multi-turn conversational RAG."""

import pytest
from researchmind.retrieval.target_paper import (
    identify_target_paper,
    TargetPaperMatch,
    has_anaphoric_reference,
    is_conversational_follow_up,
    contextualize_retrieval_query,
)
from researchmind.pipeline.rag import (
    ResearchMindRAG,
    extract_active_context_paper,
)
from researchmind.schemas.models import RetrievalCandidate


def test_has_anaphoric_reference():
    """Verify anaphora detection for pronouns and paper references."""
    assert has_anaphoric_reference("What dataset did it use?") is True
    assert has_anaphoric_reference("Can you summarize its methodology?") is True
    assert has_anaphoric_reference("What are the limitations of this paper?") is True
    assert has_anaphoric_reference("Explain the technique followed in the research paper") is True
    assert has_anaphoric_reference("What did the authors conclude?") is True
    assert has_anaphoric_reference("What are common NLP methods?") is False


def test_is_conversational_follow_up():
    """Verify conversational follow-up query detection."""
    assert is_conversational_follow_up("What are the limitations?") is True
    assert is_conversational_follow_up("Explain the results") is True
    assert is_conversational_follow_up("What dataset was used?") is True
    assert is_conversational_follow_up("Compare all papers in the database") is False


def test_context_aware_target_paper_resolution():
    """Verify that follow-up queries resolve to context paper without false clarification."""
    context = TargetPaperMatch(
        paper_id="paper_0853d9c3ae9c",
        title="GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING",
        confidence=1.0,
        is_explicit_target_query=True,
    )

    # 1. User says "What is the technique followed in the research paper?"
    # Without context, this triggered needs_clarification=True.
    # With context, it must resolve directly to context paper!
    match = identify_target_paper(
        "What is the technique followed in the research paper?",
        context_paper=context,
    )
    assert match is not None
    assert match.paper_id == "paper_0853d9c3ae9c"
    assert match.title == context.title
    assert match.needs_clarification is False

    # 2. User refers to "it" instead of name: "What dataset did it use?"
    match_it = identify_target_paper(
        "What dataset did it use?",
        context_paper=context,
    )
    assert match_it is not None
    assert match_it.paper_id == "paper_0853d9c3ae9c"
    assert match_it.needs_clarification is False

    # 3. User asks about its limitations: "What are its main limitations?"
    match_lim = identify_target_paper(
        "What are its main limitations?",
        context_paper=context,
    )
    assert match_lim is not None
    assert match_lim.paper_id == "paper_0853d9c3ae9c"
    assert match_lim.needs_clarification is False


def test_contextualize_retrieval_query():
    """Verify query rewriting for vector and lexical retrieval."""
    context = TargetPaperMatch(
        paper_id="paper_0853d9c3ae9c",
        title="GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING",
        confidence=1.0,
    )

    q_raw = "What dataset did it use?"
    q_enriched = contextualize_retrieval_query(q_raw, target_paper=context)
    assert context.title in q_enriched
    assert "What dataset did it use?" in q_enriched


def test_extract_active_context_paper_from_history():
    """Verify that extract_active_context_paper parses past turns correctly."""
    history_with_meta = [
        {"role": "user", "content": "Tell me about GEOAI building footprints"},
        {
            "role": "assistant",
            "content": "This paper presents spatial feature engineering for footprint validation...",
            "target_paper_id": "paper_0853d9c3ae9c",
            "target_paper_title": "GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING",
        },
    ]

    extracted = extract_active_context_paper(history_with_meta)
    assert extracted is not None
    assert extracted.paper_id == "paper_0853d9c3ae9c"
    assert "GEOAI-BASED" in extracted.title

    # Test history with only text content (no explicit metadata)
    history_plain = [
        {
            "role": "user",
            "content": "In the research paper GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING, how is error detected?",
        },
        {
            "role": "assistant",
            "content": "Error is detected using geometric features...",
        },
    ]

    extracted_plain = extract_active_context_paper(history_plain)
    assert extracted_plain is not None
    assert extracted_plain.paper_id == "paper_0853d9c3ae9c"


def test_multi_turn_pipeline_context_awareness():
    """Test full pipeline multi-turn query execution where turn 2 refers to 'it'."""
    rag = ResearchMindRAG()

    # Turn 1: Explicit paper mention
    turn1_query = (
        "What is the technique followed in the research paper "
        "GEOAI-BASED POST-SEGMENTATION QUALITY VALIDATION OF BUILDING FOOTPRINTS VIA SPATIAL FEATURE ENGINEERING?"
    )
    res1 = rag.query(turn1_query, retrieval_mode="hybrid_rerank")
    assert res1.abstained is False
    assert res1.target_paper_id == "paper_0853d9c3ae9c"
    assert res1.target_paper_title is not None
    assert res1.needs_clarification is False

    # Turn 2: User refers to "it" instead of name: "What dataset did it use?"
    conv_history = [
        {"role": "user", "content": turn1_query},
        {
            "role": "assistant",
            "content": res1.answer,
            "target_paper_id": res1.target_paper_id,
            "target_paper_title": res1.target_paper_title,
        },
    ]

    turn2_query = "What dataset did it use?"
    res2 = rag.query(
        turn2_query,
        retrieval_mode="hybrid_rerank",
        conversation_history=conv_history,
    )

    # Must follow context: not ask for clarification, bind to paper_0853d9c3ae9c
    assert res2.needs_clarification is False
    assert res2.target_paper_id == "paper_0853d9c3ae9c"
    assert res2.target_paper_title == res1.target_paper_title
    assert len(res2.sources) > 0
    # All retrieved chunks must be from that paper
    for src in res2.sources:
        assert src.paper_id == "paper_0853d9c3ae9c"
