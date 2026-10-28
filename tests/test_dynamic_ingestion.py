"""Tests for Dynamic Ingestion, Scope-Aware RAG, Online Discovery, and REST API."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from researchmind.schemas.models import (
    KnowledgeScope,
    IngestionJobStatus,
    ResearchChunk,
    RetrievalCandidate,
    StructuredCitation,
    ViewerReference,
)
from researchmind.discovery.base import OnlinePaperCandidate, ResearchSourceProvider
from researchmind.discovery.discovery_service import ResearchDiscoveryService
from researchmind.tasks.job_store import IngestionJobStore
from researchmind.indexing.bm25_index import BM25IndexManager
from researchmind.pipeline.rag import ResearchMindRAG
from researchmind.api.app import app


# -----------------------------------------------------------------------------
# Test 1: Ingestion Job Store Lifecycle
# -----------------------------------------------------------------------------

def test_job_store_lifecycle(tmp_path):
    store_file = tmp_path / "test_jobs.json"
    store = IngestionJobStore(store_path=store_file)

    # 1. Create job
    job = store.create_job(
        file_path="/path/to/paper1.pdf",
        file_name="paper1.pdf",
        session_id="user_123",
        scope=KnowledgeScope.USER_PAPERS,
        source="user_upload",
    )
    assert job.status == IngestionJobStatus.PENDING
    assert job.progress_pct == 0.0
    assert job.session_id == "user_123"

    # 2. Stage transitions
    stages = [
        (IngestionJobStatus.PARSING, 15.0),
        (IngestionJobStatus.CHUNKING, 40.0),
        (IngestionJobStatus.EMBEDDING, 75.0),
        (IngestionJobStatus.INDEXING, 90.0),
        (IngestionJobStatus.COMPLETED, 100.0),
    ]
    for status, pct in stages:
        updated = store.update_job(
            job.job_id,
            status=status,
            progress_pct=pct,
            current_stage=status.value.upper(),
            chunk_count=24 if status == IngestionJobStatus.COMPLETED else 0,
            paper_id="paper_abc" if status == IngestionJobStatus.COMPLETED else None,
        )
        assert updated.status == status
        assert updated.progress_pct == pct

    # 3. Retrieve and verify persistence
    loaded_job = store.get_job(job.job_id)
    assert loaded_job is not None
    assert loaded_job.status == IngestionJobStatus.COMPLETED
    assert loaded_job.chunk_count == 24
    assert loaded_job.paper_id == "paper_abc"

    # Verify session lookup
    session_jobs = store.get_session_jobs("user_123")
    assert len(session_jobs) == 1
    assert session_jobs[0].job_id == job.job_id

    # Verify empty for non-existent session
    assert len(store.get_session_jobs("other_user")) == 0


# -----------------------------------------------------------------------------
# Test 2: Online Discovery Service, Deduplication & Relevance Ranking
# -----------------------------------------------------------------------------

class MockProviderA(ResearchSourceProvider):
    def search(self, query: str, limit: int = 5):
        return [
            OnlinePaperCandidate(
                candidate_id="arxiv:2401.0001",
                title="DeepSeek-V3 Technical Report: Architecture and Innovations",
                authors=["DeepSeek AI Team"],
                year=2024,
                abstract="We present DeepSeek-V3, a strong Mixture-of-Experts (MoE) language model.",
                source="arxiv",
                identifier="2401.0001",
                pdf_url="https://arxiv.org/pdf/2401.0001.pdf",
            ),
            OnlinePaperCandidate(
                candidate_id="arxiv:2401.0002",
                title="Duplicate Paper Title Across Providers",
                authors=["Author One"],
                year=2024,
                abstract="Study on multimodal representations.",
                source="arxiv",
                identifier="2401.0002",
                pdf_url="https://arxiv.org/pdf/2401.0002.pdf",
            ),
        ]

    def get_paper_metadata(self, identifier: str):
        return None

    def download_pdf(self, candidate, target_path):
        target_path.touch()
        return target_path

    def supports_pdf(self, candidate):
        return True


class MockProviderB(ResearchSourceProvider):
    def search(self, query: str, limit: int = 5):
        return [
            OnlinePaperCandidate(
                candidate_id="s2:9999",
                title="Duplicate Paper Title Across Providers",  # Duplicate title
                authors=["Author One", "Author Two"],
                year=2024,
                abstract="Study on multimodal representations.",
                source="semantic_scholar",
                identifier="9999",
                pdf_url="https://s2.org/pdf/9999.pdf",
            ),
            OnlinePaperCandidate(
                candidate_id="s2:8888",
                title="ADOPD: Reference-Privileged On-Policy Distillation",  # Matches catalog
                authors=["Tai et al."],
                year=2026,
                abstract="Industrial anomaly detection with MLLM distillation.",
                source="semantic_scholar",
                identifier="8888",
                pdf_url="https://s2.org/pdf/8888.pdf",
            ),
        ]

    def get_paper_metadata(self, identifier: str):
        return None

    def download_pdf(self, candidate, target_path):
        target_path.touch()
        return target_path

    def supports_pdf(self, candidate):
        return True


def test_online_discovery_deduplication_and_ranking():
    service = ResearchDiscoveryService(providers=[MockProviderA(), MockProviderB()])

    results = service.search("DeepSeek architecture and distillation", max_results=10)

    # 1. Total deduplicated candidates should be 3 (DeepSeek, Duplicate Paper, ADOPD)
    assert len(results) == 3

    # 2. Check title deduplication
    titles = [r.title for r in results]
    assert len(titles) == len(set(titles))

    # 3. Check relevance ranking: DeepSeek should have high relevance for "DeepSeek architecture"
    assert results[0].title == "DeepSeek-V3 Technical Report: Architecture and Innovations"
    assert results[0].relevance_score > 0.0

    # 4. Check already_exists_locally detection for ADOPD (which exists in baseline catalog)
    adopd_candidate = next(r for r in results if "ADOPD" in r.title)
    assert adopd_candidate.already_exists_locally is True


# -----------------------------------------------------------------------------
# Test 3: Incremental BM25 Updates and Scope Pre-Filtering
# -----------------------------------------------------------------------------

def test_incremental_bm25_updates_and_scope_filtering(tmp_path):
    bm25_dir = tmp_path / "bm25_idx"
    bm25 = BM25IndexManager(index_dir=bm25_dir)

    # 1. Add baseline global chunks
    baseline_chunks = [
        ResearchChunk(
            chunk_id="chunk_base_1",
            paper_id="paper_base",
            chunk_index=0,
            text="Mixture of Experts architecture allows scaling parameters efficiently.",
            token_count=10,
            section="Architecture",
            scope="global",
            session_id="system",
        ),
        ResearchChunk(
            chunk_id="chunk_base_2",
            paper_id="paper_base",
            chunk_index=1,
            text="Reinforcement learning from human feedback aligns language models.",
            token_count=10,
            section="Training",
            scope="global",
            session_id="system",
        ),
    ]
    bm25.build_index(baseline_chunks)
    assert bm25.count() == 2

    # 2. Incrementally add user-uploaded chunks
    user_chunks = [
        ResearchChunk(
            chunk_id="chunk_user_1",
            paper_id="paper_user_new",
            chunk_index=0,
            text="Mixture of Experts routing with top-2 gating in user document.",
            token_count=11,
            section="Methods",
            scope="user_papers",
            session_id="session_alpha",
        ),
    ]
    bm25.add_chunks(user_chunks)
    assert bm25.count() == 3

    # 3. Query without filter: retrieves both
    all_results = bm25.query("Mixture of Experts", top_k=5)
    assert len(all_results) >= 2

    # 4. Scope-isolated query: user_papers only
    user_only = bm25.query("Mixture of Experts", top_k=5, where_filter={"scope": "user_papers"})
    assert len(user_only) == 1
    assert user_only[0].chunk_id == "chunk_user_1"
    assert user_only[0].paper_id == "paper_user_new"

    # 5. Paper-isolated query: allowed_paper_ids
    target_only = bm25.query("Mixture of Experts", top_k=5, allowed_paper_ids=["paper_base"])
    assert len(target_only) == 2
    assert all(c.paper_id == "paper_base" for c in target_only)


# -----------------------------------------------------------------------------
# Test 4: "This Paper Only" Strict Isolation in RAG Pipeline
# -----------------------------------------------------------------------------

class MockRetrieverTargetIsolation:
    def retrieve(self, query, top_k=20, where_filter=None, allowed_paper_ids=None):
        all_candidates = [
            RetrievalCandidate(
                chunk_id="chunk_target_1",
                paper_id="target_paper_99",
                title="Target Paper: On-Policy Distillation",
                authors=["Target Author"],
                section="3. Methodology",
                page_start=4,
                page_end=4,
                text="The teacher evaluates student-generated rollouts under matched references.",
                dense_score=0.92,
                bm25_score=0.92,
                rrf_score=0.95,
                reranker_score=0.92,
            ),
            RetrievalCandidate(
                chunk_id="chunk_other_2",
                paper_id="other_paper_88",
                title="Other Paper: Off-Policy Distillation",
                authors=["Other Author"],
                section="Methods",
                page_start=2,
                page_end=2,
                text="Standard off-policy distillation uses fixed datasets.",
                dense_score=0.88,
                bm25_score=0.88,
                rrf_score=0.91,
                reranker_score=0.88,
            ),
        ]
        # Simulate retriever filtering by allowed_paper_ids or where_filter
        if allowed_paper_ids:
            return [c for c in all_candidates if c.paper_id in allowed_paper_ids]
        if where_filter and "paper_id" in where_filter:
            return [c for c in all_candidates if c.paper_id == where_filter["paper_id"]]
        return all_candidates


class MockReranker:
    def rerank(self, query, candidates, top_k=5):
        for c in candidates:
            c.reranker_score = 0.92
            c.final_score = 0.92
        return candidates[:top_k]


class MockGeneratorWithCitations:
    def generate(self, query, candidates, target_paper=None, **kwargs):
        return (
            "In target paper on-policy distillation [C1], the teacher evaluates student rollouts "
            "under matched references to calibrate sequence-level loss.",
            {"prompt_tokens": 10, "completion_tokens": 20},
        )


def test_this_paper_only_strict_isolation():
    retriever = MockRetrieverTargetIsolation()
    generator = MockGeneratorWithCitations()
    reranker = MockReranker()

    rag = ResearchMindRAG(
        dense_retriever=retriever,
        sparse_retriever=retriever,
        hybrid_retriever=retriever,
        reranker=reranker,
        generator=generator,
    )

    response = rag.query(
        query="What is on-policy distillation in target paper?",
        knowledge_scope=KnowledgeScope.THIS_PAPER,
        scope_paper_ids=["target_paper_99"],
    )

    # 1. Must not abstain
    assert not response.abstained

    # 2. Strict isolation: all sources must be target_paper_99
    assert len(response.sources) > 0
    for source in response.sources:
        assert source.paper_id == "target_paper_99"
        assert source.paper_id != "other_paper_88"

    # 3. Structured citations must reference only target_paper_99
    assert len(response.structured_citations) > 0
    for sc in response.structured_citations:
        assert sc.paper_id == "target_paper_99"
        assert sc.viewer_reference.paper_id == "target_paper_99"
        assert sc.viewer_reference.page_number == 4


# -----------------------------------------------------------------------------
# Test 5: Insufficient Evidence & Online Search Recommendation
# -----------------------------------------------------------------------------

class MockLowRelevanceRetriever:
    def retrieve(self, query, top_k=20, where_filter=None, allowed_paper_ids=None):
        return [
            RetrievalCandidate(
                chunk_id="chunk_unrelated",
                paper_id="paper_unrelated",
                title="Unrelated Paper",
                authors=["Unrelated Author"],
                section="Intro",
                page_start=1,
                page_end=1,
                text="This document discusses completely unrelated topics.",
                dense_score=0.10,
                bm25_score=0.10,
                rrf_score=0.10,
                rerank_score=0.12,  # < threshold 0.35
            )
        ]


def test_insufficient_evidence_and_online_suggestion():
    retriever = MockLowRelevanceRetriever()
    rag = ResearchMindRAG(
        dense_retriever=retriever,
        sparse_retriever=retriever,
        hybrid_retriever=retriever,
        reranker=None,
        generator=None,
    )

    response = rag.query(
        query="Explain quantum teleportation algorithms in superconducting qubits.",
        knowledge_scope=KnowledgeScope.GLOBAL,
    )

    # 1. System must abstain due to low relevance evidence
    assert response.abstained is True
    assert response.evidence_state == "insufficient"

    # 2. Must suggest online search
    assert response.online_search_suggested is True
    assert "insufficient" in response.answer.lower() or "search online" in response.answer.lower()


# -----------------------------------------------------------------------------
# Test 6: FastAPI REST API Endpoints
# -----------------------------------------------------------------------------

def test_api_health_and_scopes():
    client = TestClient(app)

    # 1. Health check
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "scopes" in data
    assert len(data["scopes"]) == 5

    # 2. Scopes listing
    resp_scopes = client.get("/api/scopes")
    assert resp_scopes.status_code == 200
    scopes_list = resp_scopes.json()
    scope_ids = [s["id"] for s in scopes_list]
    assert "this_paper" in scope_ids
    assert "user_papers" in scope_ids
    assert "global" in scope_ids
    assert "global_plus_user" in scope_ids
    assert "global_plus_user_plus_online" in scope_ids


def test_api_papers_listing():
    client = TestClient(app)
    resp = client.get("/api/papers")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_papers" in data
    assert "papers" in data
    assert isinstance(data["papers"], list)


def test_api_ingestion_job_status():
    client = TestClient(app)
    # Non-existent job
    resp = client.get("/api/ingestion/non_existent_job_123")
    assert resp.status_code == 404
