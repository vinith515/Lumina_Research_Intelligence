"""Unified RAG and Explainable AI pipeline for ResearchMind."""

import logging
import time
from typing import List, Optional, Dict, Any, Union

from researchmind.schemas.models import (
    RetrievalMode,
    RetrievalCandidate,
    Citation,
    StructuredCitation,
    CitationScoreBreakdown,
    ViewerReference,
    KnowledgeScope,
    RAGResponse,
    XAIExplanation,
)
from researchmind.retrieval.dense import DenseRetriever
from researchmind.retrieval.sparse import SparseRetriever
from researchmind.retrieval.fusion import reciprocal_rank_fusion
from researchmind.retrieval.hybrid import HybridRetriever
from researchmind.reranking.reranker import CrossEncoderReranker
from researchmind.generation.generator import LLMGenerator
from researchmind.xai.explainer import ResearchXAIExplainer
from researchmind.config import settings

from researchmind.retrieval.target_paper import (
    identify_target_paper,
    TargetPaperMatch,
    contextualize_retrieval_query,
    PaperCatalogRegistry,
)
from researchmind.retrieval.prioritization import prioritize_candidates
import re

logger = logging.getLogger(__name__)


def extract_matched_keywords(query: str, text: str) -> List[str]:
    """Extract salient query terms matched inside the candidate passage."""
    stopwords = {
        "what", "is", "the", "in", "of", "and", "a", "an", "to", "how", "does", "do",
        "explain", "show", "tell", "which", "are", "on", "for", "with", "by", "about",
        "can", "you", "that", "this", "these", "those", "from", "at", "as", "be", "was",
        "paper", "papers", "research", "using", "used", "then", "their", "there"
    }
    words = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", query.lower())
    salient = [w for w in words if w not in stopwords]
    text_lower = text.lower()
    matched = []
    for term in salient:
        if term in text_lower and term not in matched:
            matched.append(term)
    return matched


def extract_active_context_paper(
    conversation_history: Optional[List[Union[Dict[str, Any], Any]]]
) -> Optional[TargetPaperMatch]:
    """Inspect prior conversation history to find the most recently discussed research paper."""
    if not conversation_history:
        return None

    registry = PaperCatalogRegistry.get_instance()

    # Iterate in reverse (most recent message first)
    for msg in reversed(conversation_history):
        msg_dict = msg if isinstance(msg, dict) else (msg.model_dump() if hasattr(msg, "model_dump") else {})

        # 1. Check for explicit paper attributes attached to message
        target_pid = msg_dict.get("target_paper_id")
        target_title = msg_dict.get("target_paper_title")
        if target_pid and target_title:
            return TargetPaperMatch(
                paper_id=target_pid,
                title=target_title,
                confidence=1.0,
                is_explicit_target_query=True,
                needs_clarification=False,
            )
        elif target_title:
            clean_title = str(target_title).strip()
            for entry in registry._normalized_index:
                if entry["title"].lower() == clean_title.lower() or entry["normalized_title"] == registry._normalize(clean_title):
                    return TargetPaperMatch(
                        paper_id=entry["paper_id"],
                        title=entry["title"],
                        confidence=1.0,
                        is_explicit_target_query=True,
                        needs_clarification=False,
                    )
            return TargetPaperMatch(
                paper_id="",
                title=target_title,
                confidence=1.0,
                is_explicit_target_query=True,
                needs_clarification=False,
            )

        # 2. Check content of previous turn
        content = msg_dict.get("content", "")
        if content:
            matched = identify_target_paper(content, min_confidence=0.75)
            if matched and matched.paper_id and not matched.needs_clarification:
                return matched

    return None


class ResearchMindRAG:
    """Unified scientific RAG pipeline orchestrating Dense, BM25, Hybrid RRF, Reranking, Generation, and XAI."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        generator: Optional[LLMGenerator] = None,
        explainer: Optional[ResearchXAIExplainer] = None,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.hybrid_retriever = hybrid_retriever or HybridRetriever(
            dense_retriever=self.dense_retriever,
            sparse_retriever=self.sparse_retriever,
        )
        self.reranker = reranker or CrossEncoderReranker()
        self.generator = generator or LLMGenerator()
        self.explainer = explainer or ResearchXAIExplainer()

    def query(
        self,
        query: str,
        retrieval_mode: Union[str, RetrievalMode] = RetrievalMode.HYBRID_RERANK,
        top_k: int = 5,
        dense_top_k: int = 20,
        sparse_top_k: int = 20,
        enable_xai: bool = True,
        where_filter: Optional[Dict[str, Any]] = None,
        knowledge_scope: Union[str, KnowledgeScope] = KnowledgeScope.GLOBAL,
        scope_paper_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Union[Dict[str, Any], Any]]] = None,
    ) -> RAGResponse:
        """Execute a full research query through the scope-aware RAG and XAI pipeline.
        
        Args:
            query: User's research question.
            retrieval_mode: 'dense', 'bm25', 'hybrid', or 'hybrid_rerank'.
            top_k: Final number of evidence chunks supplied to LLM.
            dense_top_k: Number of candidates retrieved by dense retriever.
            sparse_top_k: Number of candidates retrieved by BM25 retriever.
            enable_xai: Whether to compute grounding verification and XAI report.
            where_filter: Optional metadata filtering for vector retrieval.
            knowledge_scope: 'this_paper', 'my_papers', 'global', or 'global_and_my_papers'.
            scope_paper_ids: Specific list of paper IDs to isolate.
            session_id: Optional user session ID for user-scoped uploads.
            conversation_history: Optional list of prior conversation turns for context-aware multi-turn dialogue.
            
        Returns:
            Structured RAGResponse object containing answer, citations, traces, and XAI report.
        """
        start_time = time.time()
        mode_str = retrieval_mode.value if isinstance(retrieval_mode, RetrievalMode) else str(retrieval_mode).lower()
        scope_val = knowledge_scope.value if isinstance(knowledge_scope, KnowledgeScope) else str(knowledge_scope).lower()

        logger.info(f"Executing query with mode='{mode_str}', scope='{scope_val}': '{query}'")

        # Step 0: Resolve Context Paper from Prior Conversation History
        context_paper = extract_active_context_paper(conversation_history)

        # Step 0a: Identify Target Paper from query (resolving conversational anaphora/context if present)
        target_match = identify_target_paper(query, context_paper=context_paper)
        if target_match and target_match.needs_clarification:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return RAGResponse(
                query=query,
                answer=target_match.clarification_message,
                retrieval_mode=mode_str,
                evidence_state="insufficient",
                abstained=True,
                needs_clarification=True,
                knowledge_scope=scope_val,
                sources=[],
                latency_ms=latency_ms,
            )

        # Step 0b: Resolve Pre-Retrieval Scope and Document Isolation (Requirements #36, #37, #40)
        active_filter = dict(where_filter) if where_filter else {}
        allowed_paper_ids: Optional[List[str]] = None

        if scope_val == KnowledgeScope.THIS_PAPER.value:
            # Strict single-paper isolation
            target_pid = (
                scope_paper_ids[0] if (scope_paper_ids and len(scope_paper_ids) > 0)
                else (target_match.paper_id if target_match and target_match.paper_id else None)
            )
            if target_pid:
                active_filter["paper_id"] = target_pid
                allowed_paper_ids = [target_pid]
            else:
                active_filter["paper_id"] = "__NO_PAPER_SPECIFIED__"
                allowed_paper_ids = []

        elif scope_val == KnowledgeScope.MY_PAPERS.value:
            # User uploaded papers isolation
            if scope_paper_ids:
                allowed_paper_ids = scope_paper_ids
                if len(scope_paper_ids) == 1:
                    active_filter["paper_id"] = scope_paper_ids[0]
                else:
                    active_filter["paper_id"] = {"$in": scope_paper_ids}
            else:
                active_filter["scope"] = "user"
                if session_id:
                    active_filter["session_id"] = session_id

        elif scope_val == KnowledgeScope.GLOBAL.value:
            if target_match and target_match.paper_id and "paper_id" not in active_filter:
                active_filter["paper_id"] = target_match.paper_id
                allowed_paper_ids = [target_match.paper_id]

        elif scope_val == KnowledgeScope.GLOBAL_AND_MY_PAPERS.value:
            if scope_paper_ids:
                # Include specified user papers in addition to global corpus
                pass

        # Step 0c: Formulate Contextualized Retrieval Query for Embedding and Keyword Matching
        retrieval_query = contextualize_retrieval_query(
            query,
            target_paper=target_match,
            conversation_history=conversation_history,
        )

        # Step 1: Execute Scope-Restricted Retrieval
        dense_results: List[RetrievalCandidate] = []
        sparse_results: List[RetrievalCandidate] = []
        hybrid_results: List[RetrievalCandidate] = []
        final_evidence: List[RetrievalCandidate] = []

        active_where = active_filter if active_filter else None

        if mode_str == "bm25":
            try:
                sparse_results = self.sparse_retriever.retrieve(
                    retrieval_query,
                    top_k=max(sparse_top_k, top_k),
                    allowed_paper_ids=allowed_paper_ids,
                )
            except TypeError:
                sparse_results = self.sparse_retriever.retrieve(retrieval_query, top_k=max(sparse_top_k, top_k))
            final_evidence = sparse_results

        elif mode_str == "dense":
            try:
                dense_results = self.dense_retriever.retrieve(
                    retrieval_query,
                    top_k=max(dense_top_k, top_k),
                    where_filter=active_where,
                )
            except TypeError:
                dense_results = self.dense_retriever.retrieve(retrieval_query, top_k=max(dense_top_k, top_k))
            final_evidence = dense_results

        elif mode_str == "hybrid":
            try:
                dense_results = self.dense_retriever.retrieve(
                    retrieval_query,
                    top_k=dense_top_k,
                    where_filter=active_where,
                )
            except TypeError:
                dense_results = self.dense_retriever.retrieve(retrieval_query, top_k=dense_top_k)

            try:
                sparse_results = self.sparse_retriever.retrieve(
                    retrieval_query,
                    top_k=sparse_top_k,
                    allowed_paper_ids=allowed_paper_ids,
                )
            except TypeError:
                sparse_results = self.sparse_retriever.retrieve(retrieval_query, top_k=sparse_top_k)

            hybrid_results = reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                k=settings.RRF_K,
                top_k=max(top_k * 3, 15),
            )
            final_evidence = hybrid_results

        elif mode_str in ["hybrid_rerank", "hybrid+reranker"]:
            try:
                dense_results = self.dense_retriever.retrieve(
                    retrieval_query,
                    top_k=dense_top_k,
                    where_filter=active_where,
                )
            except TypeError:
                dense_results = self.dense_retriever.retrieve(retrieval_query, top_k=dense_top_k)

            try:
                sparse_results = self.sparse_retriever.retrieve(
                    retrieval_query,
                    top_k=sparse_top_k,
                    allowed_paper_ids=allowed_paper_ids,
                )
            except TypeError:
                sparse_results = self.sparse_retriever.retrieve(retrieval_query, top_k=sparse_top_k)

            hybrid_candidates = reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                k=settings.RRF_K,
                top_k=max(top_k * 3, 15),
            )
            hybrid_results = hybrid_candidates
            final_evidence = self.reranker.rerank(
                query=retrieval_query,
                candidates=hybrid_candidates,
                top_k=max(top_k * 2, 10),
            )

        else:
            raise ValueError(f"Unknown retrieval mode: {retrieval_mode}. Supported: dense, bm25, hybrid, hybrid_rerank")

        # Step 1b: Target Paper Strict Post-Retrieval Enforcement
        if allowed_paper_ids is not None:
            final_evidence = [c for c in final_evidence if c.paper_id in allowed_paper_ids]

        # Step 1c: Methodology Section Prioritization Boosting (Requirement B)
        final_evidence = prioritize_candidates(final_evidence, query=query, top_k=top_k)

        # Step 2: Evidence Sufficiency Decision (Requirements #2, #16, #53)
        top_score = 0.0
        if final_evidence:
            top_cand = final_evidence[0]
            top_score = (
                top_cand.reranker_score if top_cand.reranker_score is not None
                else (top_cand.dense_score if top_cand.dense_score is not None else top_cand.final_score)
            )

        is_insufficient = (not final_evidence) or (top_score < settings.EVIDENCE_SUFFICIENCY_THRESHOLD)
        online_search_suggested = False

        if is_insufficient:
            if scope_val == KnowledgeScope.THIS_PAPER.value:
                answer_text = "I couldn't find sufficient evidence in this paper to answer that question."
                online_search_suggested = False
            else:
                answer_text = (
                    "I couldn't find sufficient evidence in the current ResearchMind database to answer this question reliably. "
                    "Would you like me to search online research sources such as arXiv or Semantic Scholar for relevant papers?"
                )
                online_search_suggested = True

            token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        else:
            # Step 2b: Grounded LLM Generation with retrieved evidence and conversation history
            answer_text, token_usage = self.generator.generate(
                query=query,
                candidates=final_evidence,
                target_paper=target_match,
                conversation_history=conversation_history,
            )

        # Step 3: Build Verified and Structured Citations with Granular Score Breakdowns
        citations: List[Citation] = []
        structured_citations: List[StructuredCitation] = []

        is_abstaining_answer = (
            is_insufficient
            or answer_text.strip().lower().startswith("i couldn't find sufficient evidence")
            or "couldn't find sufficient evidence" in answer_text.lower()
        )

        if not is_abstaining_answer:
            for idx, c in enumerate(final_evidence, start=1):
                cit_id = f"C{idx}"
                viewer_ref = ViewerReference(
                    paper_id=c.paper_id,
                    page=c.page_start,
                    page_number=c.page_start,
                    text=c.text[:150],
                    snippet=c.text[:150],
                    bbox=c.bbox,
                )
                matched_kws = extract_matched_keywords(query, c.text)
                score_breakdown = CitationScoreBreakdown(
                    dense_score=c.dense_score,
                    dense_rank=c.dense_rank,
                    bm25_score=c.bm25_score,
                    bm25_rank=c.bm25_rank,
                    rrf_score=c.rrf_score,
                    rrf_rank=c.rrf_rank,
                    reranker_score=c.reranker_score,
                    reranker_rank=c.reranker_rank,
                    final_confidence=round((c.final_score if c.final_score is not None else 0.5) * 100, 1),
                    section_boost_applied=getattr(c, "section_boost", None),
                )
                score_label = f"Cross-Encoder score {c.reranker_score:.3f}" if c.reranker_score is not None else f"relevance {c.final_score:.3f}"
                kw_note = f" Matches query keywords: [{', '.join(matched_kws[:4])}]." if matched_kws else ""
                default_rationale = (
                    f"Selected as citation [{cit_id}] from '{c.title}' ({c.section or 'General'}, p. {c.page_start}) "
                    f"with {score_label}. High semantic density prioritizes this passage over general narrative.{kw_note}"
                )

                # Legacy Citation model
                citations.append(
                    Citation(
                        paper_id=c.paper_id,
                        title=c.title,
                        authors=c.authors,
                        page_start=c.page_start,
                        page_end=c.page_end,
                        section=c.section,
                        subsection=c.subsection,
                        chunk_id=c.chunk_id,
                        retrieval_score=c.final_score,
                        retrieval_method=mode_str,
                        snippet=c.text[:180] + "...",
                        citation_id=cit_id,
                        scope=c.scope,
                        source=c.source,
                        viewer_reference=viewer_ref,
                        score_breakdown=score_breakdown,
                        selection_rationale=default_rationale,
                        matched_keywords=matched_kws,
                        supported_claims=[],
                    )
                )
                # Structured citation for UI with PDF viewer linking
                structured_citations.append(
                    StructuredCitation(
                        citation_id=cit_id,
                        paper_id=c.paper_id,
                        title=c.title,
                        authors=c.authors,
                        page_start=c.page_start,
                        page_end=c.page_end,
                        section=c.section,
                        subsection=c.subsection,
                        chunk_id=c.chunk_id,
                        retrieval_score=c.final_score,
                        retrieval_method=mode_str,
                        snippet=c.text[:180] + "...",
                        scope=c.scope,
                        source=c.source,
                        viewer_reference=viewer_ref,
                        score_breakdown=score_breakdown,
                        selection_rationale=default_rationale,
                        matched_keywords=matched_kws,
                        supported_claims=[],
                    )
                )

        # Step 4: Explainable AI (XAI) Generation
        xai_report: Optional[XAIExplanation] = None
        evidence_state = "insufficient" if (is_insufficient or is_abstaining_answer) else "moderate"
        abstained = is_insufficient or is_abstaining_answer
        comp_assessment = None

        if enable_xai and settings.ENABLE_XAI and not is_insufficient:
            provider_status = getattr(self.generator, "last_provider_status", "api_success")
            xai_report = self.explainer.generate_explanation(
                query=query,
                answer=answer_text,
                dense_results=dense_results,
                sparse_results=sparse_results,
                hybrid_results=hybrid_results,
                final_evidence=final_evidence,
                target_paper_id=target_match.paper_id if target_match else None,
                target_paper_title=target_match.title if target_match else None,
                provider_status=provider_status,
            )
            if xai_report:
                evidence_state = xai_report.evidence_state
                abstained = xai_report.abstained
                comp_assessment = xai_report.component_assessment

                # Backpropagate grounded claims and rationales into structured citations
                chunk_map = {c.chunk_id: (citations[i], structured_citations[i]) for i, c in enumerate(final_evidence)}
                for claim_exp in xai_report.claim_explanations:
                    for chk_id in claim_exp.supporting_chunk_ids:
                        if chk_id in chunk_map:
                            cit_item, sc_item = chunk_map[chk_id]
                            if claim_exp.claim_index not in cit_item.supported_claims:
                                cit_item.supported_claims.append(claim_exp.claim_index)
                            if claim_exp.claim_index not in sc_item.supported_claims:
                                sc_item.supported_claims.append(claim_exp.claim_index)

                for i, sc_item in enumerate(structured_citations):
                    if sc_item.citation_id in xai_report.citation_rationales:
                        sc_item.selection_rationale = xai_report.citation_rationales[sc_item.citation_id]
                        citations[i].selection_rationale = xai_report.citation_rationales[sc_item.citation_id]
        elif is_insufficient:
            lower_ans = answer_text.lower()
            abstained = True
            evidence_state = "insufficient"

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return RAGResponse(
            query=query,
            answer=answer_text,
            retrieval_mode=mode_str,
            evidence_state=evidence_state,
            abstained=abstained,
            target_paper_id=target_match.paper_id if (target_match and target_match.paper_id) else (
                allowed_paper_ids[0] if (allowed_paper_ids and len(allowed_paper_ids) > 0) else (final_evidence[0].paper_id if final_evidence else None)
            ),
            target_paper_title=target_match.title if (target_match and target_match.title) else (
                final_evidence[0].title if final_evidence else None
            ),
            needs_clarification=False,
            knowledge_scope=scope_val,
            scope_paper_ids=allowed_paper_ids or [],
            online_search_suggested=online_search_suggested,
            sources=citations,
            structured_citations=structured_citations,
            xai_explanation=xai_report,
            component_assessment=comp_assessment,
            latency_ms=latency_ms,
            token_usage=token_usage,
        )

