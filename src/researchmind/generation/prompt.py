"""Prompt construction and templates for grounded research generation adhering to the 3 Evidence States."""

from typing import List, Optional, Dict, Any
from researchmind.schemas.models import RetrievalCandidate

ACADEMIC_SYSTEM_PROMPT = """You are Lumina, an expert AI research assistant. Your task is to provide accurate, strictly grounded, and explainable answers to research questions based ONLY on the provided research paper excerpts.

CORE OPERATIONAL EVIDENCE STATES:
You must strictly adhere to one of three evidence states based on the retrieved research context:

1. STATE A — STRONG / SUFFICIENT EVIDENCE:
   - If the retrieved sources provide clear, direct, and sufficient evidence to answer the question, provide a structured, thorough answer.
   - Cite every claim inline using bracketed indices (e.g. [1], [2]) with page numbers when available (e.g. [1, p.5]).
   - Clearly distinguish between direct findings (e.g., "Source [1] reports that...") and multi-paper synthesis (e.g., "Synthesizing these findings indicates...").

2. STATE B — PARTIAL / MODERATE EVIDENCE:
   - If the corpus contains related evidence but does NOT completely answer every aspect of the question:
     a) State what the retrieved evidence supports with exact citations.
     b) Explicitly declare what is NOT established or missing from the available papers (evidence gaps).
   - CRITICAL: Do NOT attempt to fill in missing details using your pretrained general knowledge.

3. STATE C — INSUFFICIENT EVIDENCE / OUT-OF-CORPUS:
   - If the retrieved excerpts do not contain relevant or sufficient evidence to answer the question reliably (or if the question is outside the research literature corpus):
   - Explicitly abstain by stating: "I couldn't find sufficient evidence in the Lumina research corpus to answer this question reliably."
   - Disclose that the available sources do not establish the requested information.
   - CRITICAL: Do NOT generate a generic textbook answer from pretrained world knowledge.

GENERAL RULES:
- Never invent facts, numbers, benchmarks, or citations not present in the excerpts.
- Maintain an objective, concise, and academically rigorous tone."""


def build_research_context(candidates: List[RetrievalCandidate]) -> str:
    """Format retrieved candidates into structured citation source blocks."""
    if not candidates:
        return "No relevant research sources found in the corpus."

    source_blocks = []
    for idx, c in enumerate(candidates, start=1):
        block = (
            f"CITATION [C{idx}] (Source [{idx}])\n"
            f"Paper Title: {c.title}\n"
            f"Section: {c.section}" + (f" -> {c.subsection}" if c.subsection else "") + "\n"
            f"Page(s): {c.page_start}" + (f"-{c.page_end}" if c.page_end != c.page_start else "") + "\n"
            f"Scope: {getattr(c, 'scope', 'global')} | Source: {getattr(c, 'source', 'corpus')}\n"
            f"Chunk ID: {c.chunk_id}\n"
            f"Normalized Relevance Score: {c.reranker_score if c.reranker_score is not None else c.final_score:.4f}\n"
            f"Evidence Content:\n{c.text.strip()}"
        )
        source_blocks.append(block)

    return "\n\n" + ("=" * 40) + "\n\n".join(source_blocks) + "\n\n" + ("=" * 40)


def build_user_prompt(
    query: str,
    context: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    target_paper: Optional[Any] = None,
) -> str:
    """Build user message containing research query, conversational context, and retrieved evidence."""
    context_sections = []

    # 1. Format prior dialogue turns if conversation history is present
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "").strip()
            if not content:
                continue
            if len(content) > 600:
                content = content[:600] + "..."
            history_lines.append(f"{role}: {content}")
        if history_lines:
            context_sections.append("PRIOR CONVERSATION HISTORY:\n" + "\n".join(history_lines))

    # 2. Focus research paper under discussion
    paper_title = None
    if target_paper:
        paper_title = getattr(target_paper, "title", str(target_paper) if target_paper else None)
    if paper_title:
        context_sections.append(f"ACTIVE FOCUS RESEARCH PAPER: {paper_title}")

    # 3. Current research query
    context_sections.append(f"CURRENT RESEARCH QUERY:\n{query}")

    # 4. Retrieved evidence
    context_sections.append(f"RETRIEVED RESEARCH PAPER EVIDENCE:\n{context}")

    body = "\n\n".join(context_sections)

    return f"""{body}

Please formulate your response adhering strictly to the Three Evidence States (State A for sufficient evidence, State B for partial evidence with explicit gaps, or State C for insufficient evidence / abstention). Include precise citations using the provided citation tags [C1], [C2], etc. (or [1], [2]). Since this query is part of an ongoing conversation, maintain conversational coherence (e.g., resolving pronouns like 'it' or 'the paper' to the active focus paper) while strictly grounding all assertions in the retrieved evidence."""
