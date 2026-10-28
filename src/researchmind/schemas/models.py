"""Data models and schemas for ResearchMind."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Types of structured elements extracted by Unstructured."""
    TITLE = "Title"
    NARRATIVE_TEXT = "NarrativeText"
    TEXT = "Text"
    HEADER = "Header"
    FOOTER = "Footer"
    LIST_ITEM = "ListItem"
    TABLE = "Table"
    FIGURE_CAPTION = "FigureCaption"
    FORMULA = "Formula"
    PAGE_BREAK = "PageBreak"
    ABSTRACT = "Abstract"
    SECTION_HEADER = "SectionHeader"
    CODE_SNIPPET = "CodeSnippet"
    UNCATEGORIZED = "UncategorizedText"


class KnowledgeScope(str, Enum):
    """Knowledge scopes for user queries and document isolation."""
    THIS_PAPER = "this_paper"                       # Strict single paper
    MY_PAPERS = "my_papers"                         # All papers uploaded by user/session
    USER_PAPERS = "user_papers"                     # Alias for my_papers
    GLOBAL = "global"                               # ResearchMind shared corpus
    GLOBAL_AND_MY_PAPERS = "global_and_my_papers"   # ResearchMind + user uploaded papers
    GLOBAL_PLUS_USER = "global_plus_user"           # Alias for global_and_my_papers
    ONLINE_EXPANSION = "online_expansion"           # ResearchMind + my papers + online search
    GLOBAL_PLUS_USER_PLUS_ONLINE = "global_plus_user_plus_online" # Alias


class IngestionJobStatus(str, Enum):
    """Lifecycle states for asynchronous document ingestion jobs."""
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionJob(BaseModel):
    """Status record and progress tracking for Celery ingestion tasks."""
    job_id: str
    paper_id: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    source: str = "user_upload"   # 'user_upload', 'arxiv', 'semantic_scholar', 'corpus'
    scope: str = "user"           # 'user' or 'global'
    session_id: Optional[str] = None
    status: IngestionJobStatus = IngestionJobStatus.PENDING
    progress_percent: int = 0
    progress_pct: float = 0.0
    status_message: str = "Queued for ingestion"
    current_stage: str = "PENDING"
    total_pages: int = 0
    total_chunks: int = 0
    chunk_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentElement(BaseModel):
    """An individual structured element extracted from a research paper PDF."""
    paper_id: str
    element_id: str
    element_type: str = ElementType.NARRATIVE_TEXT.value
    text: str
    page_number: int = 1
    coordinates: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaperMetadata(BaseModel):
    """High-level metadata for a research paper."""
    paper_id: str
    filename: str
    file_path: str
    file_hash: str
    category: str = "General"
    title: str = "Untitled Paper"
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    journal_or_conference: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    paper_url: Optional[str] = None
    pdf_url: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    total_pages: int = 0
    total_elements: int = 0
    total_chunks: int = 0
    scope: str = "global"  # 'global' (standard corpus) or 'user' (user session upload)
    session_id: Optional[str] = None
    source: str = "corpus"  # 'corpus', 'user_upload', 'arxiv', 'semantic_scholar'
    status: str = "pending"  # pending, processed, failed, duplicate
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResearchChunk(BaseModel):
    """A semantically coherent chunk of a research paper with full provenance."""
    chunk_id: str
    paper_id: str
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    section: str = "General"
    subsection: Optional[str] = None
    page_start: int = 1
    page_end: int = 1
    element_types: List[str] = Field(default_factory=list)
    text: str
    chunk_index: int = 0
    token_count: int = 0
    char_count: int = 0
    scope: str = "global"  # 'global' or 'user'
    session_id: Optional[str] = None
    source: str = "corpus"
    bbox: Optional[List[Any]] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalMode(str, Enum):
    """Supported retrieval execution modes."""
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"


class RetrievalCandidate(BaseModel):
    """Candidate chunk with detailed multi-stage retrieval signals and provenance."""
    chunk_id: str
    paper_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    section: str
    subsection: Optional[str] = None
    page_start: int
    page_end: int
    text: str
    scope: str = "global"
    session_id: Optional[str] = None
    source: str = "corpus"
    bbox: Optional[List[Any]] = None
    
    # Stage Scores & Ranks
    dense_score: Optional[float] = None
    dense_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rrf_rank: Optional[int] = None
    reranker_score: Optional[float] = None
    reranker_rank: Optional[int] = None
    
    final_score: float = 0.0
    final_rank: int = 0
    retrieval_rationale: str = ""


class ViewerReference(BaseModel):
    """Exact spatial coordinates and text anchor for in-viewer PDF navigation and highlighting."""
    paper_id: Optional[str] = None
    page: int = 1
    page_number: int = 1
    text: str = ""
    snippet: str = ""
    bbox: Optional[List[Any]] = None


class CitationScoreBreakdown(BaseModel):
    """Granular multi-stage retrieval and reranking score breakdown for an individual citation."""
    dense_score: Optional[float] = None
    dense_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rrf_rank: Optional[int] = None
    reranker_score: Optional[float] = None
    reranker_rank: Optional[int] = None
    final_confidence: float = 0.0
    section_boost_applied: Optional[float] = None


class StructuredCitation(BaseModel):
    """Rich citation object with deterministic identifier [C1], PDF navigation anchors, and selection rationales."""
    citation_id: str  # e.g. "C1", "C2"
    paper_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    page_start: int
    page_end: int
    section: str
    subsection: Optional[str] = None
    chunk_id: str
    retrieval_score: float
    retrieval_method: str = "hybrid_rerank"
    snippet: str = ""
    scope: str = "global"
    source: str = "corpus"
    viewer_reference: Optional[ViewerReference] = None
    score_breakdown: Optional[CitationScoreBreakdown] = None
    selection_rationale: str = ""
    matched_keywords: List[str] = Field(default_factory=list)
    supported_claims: List[int] = Field(default_factory=list)


class Citation(BaseModel):
    """Verified, traceable citation pointing to specific paper sections and pages."""
    paper_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    page_start: int
    page_end: int
    section: str
    subsection: Optional[str] = None
    chunk_id: str
    retrieval_score: float
    retrieval_method: str = "hybrid_rerank"
    snippet: str = ""
    citation_id: Optional[str] = None
    scope: str = "global"
    source: str = "corpus"
    viewer_reference: Optional[ViewerReference] = None
    score_breakdown: Optional[CitationScoreBreakdown] = None
    selection_rationale: str = ""
    matched_keywords: List[str] = Field(default_factory=list)
    supported_claims: List[int] = Field(default_factory=list)


class EvidenceStrength(str, Enum):
    """Calibrated evidence confidence level."""
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    INSUFFICIENT = "Insufficient"


class ComponentQualityAssessment(BaseModel):
    """Qualitative evaluation of system components to avoid unjustified 'Strong' evidence labels."""
    gemini_availability: str = "Available (API Success)"
    citation_generation: str = "Functioning"
    target_paper_relevance: str = "Verified"
    methodology_extraction: str = "Sufficient"
    cross_paper_contamination: str = "None detected"
    overall_answer_quality: str = "High"


class ClaimExplanation(BaseModel):
    """Explanation of a specific claim in the generated answer and its supporting evidence."""
    claim: str
    claim_index: int
    is_grounded: bool = True
    is_supported_by_passage: bool = True
    answers_question: bool = True
    belongs_to_target_paper: bool = True
    supporting_chunk_ids: List[str] = Field(default_factory=list)
    supporting_citations: List[Citation] = Field(default_factory=list)
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    rationale: str = ""
    verification_method: str = "Lexical Grounding Heuristic"


class GroundingAssessment(BaseModel):
    """Grounding assessment summary across all generated claims."""
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    grounded_ratio: float = 1.0
    evidence_strength_overall: EvidenceStrength = EvidenceStrength.MODERATE
    verification_method: str = "Lexical Grounding Heuristic"
    hallucination_warning: Optional[str] = None
    target_paper_id: Optional[str] = None
    target_paper_title: Optional[str] = None
    component_assessment: Optional[ComponentQualityAssessment] = None


class RetrievalStageResult(BaseModel):
    """Summary of chunks retrieved at a particular stage."""
    stage_name: str
    candidates: List[RetrievalCandidate] = Field(default_factory=list)


class XAIExplanation(BaseModel):
    """Complete Explainable AI report for a research query."""
    query: str
    retrieval_explanation: Dict[str, Any] = Field(default_factory=dict)
    final_evidence: List[RetrievalCandidate] = Field(default_factory=list)
    claim_explanations: List[ClaimExplanation] = Field(default_factory=list)
    grounding: GroundingAssessment = Field(default_factory=GroundingAssessment)
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    evidence_state: str = "moderate"
    abstained: bool = False
    faithfulness_score: float = 100.0
    retrieval_funnel: Dict[str, Any] = Field(default_factory=dict)
    contrastive_insights: List[str] = Field(default_factory=list)
    citation_rationales: Dict[str, str] = Field(default_factory=dict)
    component_assessment: Optional[ComponentQualityAssessment] = None
    human_readable_report: str = ""


class RAGResponse(BaseModel):
    """Complete RAG response with answer, citations, XAI explanations and traces."""
    query: str
    answer: str
    retrieval_mode: str
    evidence_state: str = "moderate"
    abstained: bool = False
    target_paper_id: Optional[str] = None
    target_paper_title: Optional[str] = None
    needs_clarification: bool = False
    knowledge_scope: str = "global"
    scope_paper_ids: List[str] = Field(default_factory=list)
    online_search_suggested: bool = False
    sources: List[Citation] = Field(default_factory=list)
    structured_citations: List[StructuredCitation] = Field(default_factory=list)
    xai_explanation: Optional[XAIExplanation] = None
    component_assessment: Optional[ComponentQualityAssessment] = None
    latency_ms: float = 0.0
    token_usage: Dict[str, int] = Field(default_factory=dict)


class EvaluationQuery(BaseModel):
    """Benchmark query definition for evaluation."""
    query_id: str
    query: str
    domain: str = "General"
    category: Optional[str] = None
    relevant_paper_ids: List[str] = Field(default_factory=list)
    relevant_chunk_ids: List[str] = Field(default_factory=list)
    relevant_pages: List[int] = Field(default_factory=list)
    relevant_sections: List[str] = Field(default_factory=list)
    ground_truth_answer: Optional[str] = None
    answerability: str = "answerable"  # 'answerable', 'partial', 'unanswerable'
    split: str = "test"  # 'validation', 'test'
    annotation_type: str = "human-verified"  # 'human-verified', 'LLM-assisted'
    notes: Optional[str] = None


class EvaluationResult(BaseModel):
    """Evaluation metrics for a specific retrieval configuration."""
    method: str
    eval_level: str = "paper"  # 'paper' or 'chunk'
    query_count: int = 0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    recall_at_20: float = 0.0
    precision_at_5: float = 0.0
    hit_rate_at_5: float = 0.0
    hit_rate_at_10: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    grounded_claim_percentage: Optional[float] = None
    citation_precision: Optional[float] = None
    abstention_accuracy: Optional[float] = None
    selective_accuracy: Optional[float] = None
    unsupported_answer_rate: Optional[float] = None
    false_abstention_rate: Optional[float] = None
    avg_latency_ms: float = 0.0

