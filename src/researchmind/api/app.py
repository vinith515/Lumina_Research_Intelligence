"""FastAPI application for ResearchMind dynamic RAG and research discovery."""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from researchmind.config import settings
from researchmind.schemas.models import (
    KnowledgeScope,
    IngestionJobStatus,
    IngestionJob,
    StructuredCitation,
    RAGResponse,
    XAIExplanation,
    ComponentQualityAssessment,
)
from researchmind.pipeline.rag import ResearchMindRAG
from researchmind.discovery.discovery_service import ResearchDiscoveryService
from researchmind.discovery.base import OnlinePaperCandidate
from researchmind.tasks.job_store import IngestionJobStore
from researchmind.tasks.ingestion_tasks import dispatch_ingestion_task
from researchmind.database.user_history_db import UserHistoryDatabase

logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Lumina API",
    description="Dynamic Research-Paper Ingestion and Grounded RAG Platform",
    version="2.0.0",
)

# Enable CORS for local development and web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global lazy singletons
_rag_pipeline: Optional[ResearchMindRAG] = None
_discovery_service: Optional[ResearchDiscoveryService] = None
_job_store: Optional[IngestionJobStore] = None
_paper_catalog_cache: Optional[Dict[str, Any]] = None
_history_db: Optional[UserHistoryDatabase] = None


def get_history_db() -> UserHistoryDatabase:
    global _history_db
    if _history_db is None:
        _history_db = UserHistoryDatabase.get_instance()
    return _history_db


def get_rag_pipeline() -> ResearchMindRAG:
    global _rag_pipeline
    if _rag_pipeline is None:
        logger.info("Initializing ResearchMindRAG pipeline...")
        _rag_pipeline = ResearchMindRAG()
    return _rag_pipeline


def get_discovery_service() -> ResearchDiscoveryService:
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = ResearchDiscoveryService()
    return _discovery_service


def get_job_store() -> IngestionJobStore:
    global _job_store
    if _job_store is None:
        _job_store = IngestionJobStore()
    return _job_store


def get_catalog() -> Dict[str, Any]:
    global _paper_catalog_cache
    if _paper_catalog_cache is None:
        catalog_path = settings.metadata_path / "catalog.json"
        if catalog_path.exists():
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    _paper_catalog_cache = json.load(f)
            except Exception as e:
                logger.error(f"Error loading catalog.json: {e}")
                _paper_catalog_cache = {}
        else:
            _paper_catalog_cache = {}
    return _paper_catalog_cache


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------

class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    target_paper_id: Optional[str] = None
    target_paper_title: Optional[str] = None


class QueryApiRequest(BaseModel):
    query: str
    knowledge_scope: str = KnowledgeScope.GLOBAL.value
    scope_paper_ids: Optional[List[str]] = None
    session_id: Optional[str] = "default_user"
    user_email: Optional[str] = None
    top_k: int = 5
    retrieval_mode: str = "hybrid_rerank"
    conversation_history: Optional[List[ChatHistoryMessage]] = None


class QueryApiResponse(BaseModel):
    query: str
    answer: str
    retrieval_mode: str
    evidence_state: str
    abstained: bool
    target_paper_id: Optional[str] = None
    target_paper_title: Optional[str] = None
    needs_clarification: bool = False
    knowledge_scope: str
    scope_paper_ids: List[str] = Field(default_factory=list)
    online_search_suggested: bool = False
    suggested_query: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    structured_citations: List[StructuredCitation] = Field(default_factory=list)
    latency_ms: float = 0.0
    faithfulness_score: Optional[float] = None
    xai_explanation: Optional[XAIExplanation] = None
    component_assessment: Optional[ComponentQualityAssessment] = None


class SearchOnlineApiRequest(BaseModel):
    query: str
    provider: Optional[str] = "all"
    max_results: Optional[int] = 5


class IngestOnlineApiRequest(BaseModel):
    candidates: List[OnlinePaperCandidate]
    session_id: Optional[str] = "default_user"
    ingestion_mode: Optional[str] = "permanent"  # "permanent" (database) or "session_only" (temporary)


# ---------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """System health check and status."""
    catalog = get_catalog()
    jobs = get_job_store().get_all_jobs()
    return {
        "status": "healthy",
        "service": "Lumina API",
        "version": "2.0.0",
        "baseline_papers_count": len(catalog),
        "total_ingestion_jobs": len(jobs),
        "scopes": [
            KnowledgeScope.THIS_PAPER.value,
            KnowledgeScope.USER_PAPERS.value,
            KnowledgeScope.GLOBAL.value,
            KnowledgeScope.GLOBAL_PLUS_USER.value,
            KnowledgeScope.GLOBAL_PLUS_USER_PLUS_ONLINE.value,
        ],
    }


@app.get("/api/scopes")
async def get_scopes():
    """List available knowledge scopes with descriptions."""
    return [
        {
            "id": KnowledgeScope.THIS_PAPER.value,
            "label": "This Paper Only",
            "description": "Strictly isolates retrieval to one targeted paper. No cross-corpus noise.",
            "color": "indigo",
        },
        {
            "id": KnowledgeScope.USER_PAPERS.value,
            "label": "My Uploaded Papers",
            "description": "Searches only research papers uploaded during your active session.",
            "color": "emerald",
        },
        {
            "id": KnowledgeScope.GLOBAL.value,
            "label": "Lumina Knowledge Base",
            "description": "Searches the 48,000+ chunk pre-indexed peer-reviewed paper corpus.",
            "color": "sky",
        },
        {
            "id": KnowledgeScope.GLOBAL_PLUS_USER.value,
            "label": "Lumina + My Uploaded Papers",
            "description": "Combines baseline scientific literature with your custom uploaded papers.",
            "color": "amber",
        },
        {
            "id": KnowledgeScope.GLOBAL_PLUS_USER_PLUS_ONLINE.value,
            "label": "Lumina + My Papers + Online Research",
            "description": "Full synthesis across baseline corpus, uploads, and imported arXiv/S2 papers.",
            "color": "rose",
        },
    ]


@app.post("/api/query", response_model=QueryApiResponse)
async def execute_query(req: QueryApiRequest):
    """Execute a scope-aware grounded RAG query with structured citation output."""
    rag = get_rag_pipeline()
    try:
        # Extract and format conversation history
        conv_history: Optional[List[Dict[str, Any]]] = None
        if req.conversation_history:
            conv_history = [m.model_dump() for m in req.conversation_history]
        elif req.session_id:
            # Fall back to SQLite session history if client didn't supply an explicit message thread
            try:
                h_db = get_history_db()
                last_q = h_db.get_last_query_for_session(req.session_id)
                if last_q:
                    conv_history = [
                        {"role": "user", "content": last_q["query_text"]},
                        {
                            "role": "assistant",
                            "content": last_q["answer_text"][:500],
                            "target_paper_title": last_q.get("target_paper_title"),
                        },
                    ]
            except Exception as e_hist_lookup:
                logger.debug(f"Could not load previous session query for context: {e_hist_lookup}")

        response: RAGResponse = rag.query(
            query=req.query,
            retrieval_mode=req.retrieval_mode,
            top_k=req.top_k,
            knowledge_scope=req.knowledge_scope,
            scope_paper_ids=req.scope_paper_ids,
            session_id=req.session_id,
            conversation_history=conv_history,
        )

        sources_data = [s.model_dump() for s in response.sources]

        # Formulate suggested query for external search if abstained
        suggested_q = None
        if response.online_search_suggested:
            suggested_q = req.query.strip().rstrip("?").replace("what is", "").replace("explain", "").strip()

        # Persist query and grounded answer to SQLite user history database
        try:
            h_db = get_history_db()
            citations_dicts = [c.model_dump() for c in response.structured_citations]
            h_db.record_query(
                user_email=req.user_email or "guest@lumina.ai",
                session_id=req.session_id,
                query_text=response.query,
                answer_text=response.answer,
                evidence_state=response.evidence_state,
                knowledge_scope=response.knowledge_scope,
                retrieval_mode=response.retrieval_mode,
                target_paper_title=response.target_paper_title,
                latency_ms=response.latency_ms,
                abstained=response.abstained,
                citations=citations_dicts,
                sources=sources_data,
            )
        except Exception as e_hist:
            logger.warning(f"Could not record query to SQLite history: {e_hist}")

        return QueryApiResponse(
            query=response.query,
            answer=response.answer,
            retrieval_mode=response.retrieval_mode,
            evidence_state=response.evidence_state,
            abstained=response.abstained,
            target_paper_id=response.target_paper_id,
            target_paper_title=response.target_paper_title,
            needs_clarification=response.needs_clarification,
            knowledge_scope=response.knowledge_scope,
            scope_paper_ids=response.scope_paper_ids,
            online_search_suggested=response.online_search_suggested,
            suggested_query=suggested_q,
            sources=sources_data,
            structured_citations=response.structured_citations,
            latency_ms=response.latency_ms,
            faithfulness_score=response.xai_explanation.faithfulness_score if response.xai_explanation else None,
            xai_explanation=response.xai_explanation,
            component_assessment=response.component_assessment,
        )
    except Exception as e:
        logger.exception("Error executing RAG query")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/papers/upload")
async def upload_paper(
    file: UploadFile = File(...),
    session_id: str = Form("default_user"),
    ingestion_mode: str = Form("permanent"),
    user_email: Optional[str] = Form(None),
):
    """Upload a research paper PDF and initiate background ingestion."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    upload_dir = settings.user_upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Clean destination file name
    safe_filename = Path(file.filename).name
    dest_path = upload_dir / safe_filename

    # Save uploaded file
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Determine scope based on user's choice: permanent -> global database; session_only -> user session
    is_perm = ingestion_mode.lower() in ("permanent", "database", "global")
    target_scope = "global" if is_perm else "user"
    scope_enum = KnowledgeScope.GLOBAL if is_perm else KnowledgeScope.USER_PAPERS
    target_session = None if is_perm else session_id

    # Register ingestion job
    job_store = get_job_store()
    job = job_store.create_job(
        file_path=str(dest_path),
        file_name=safe_filename,
        session_id=target_session,
        scope=scope_enum,
        source="user_upload",
    )

    # Record into SQLite upload_history
    try:
        h_db = get_history_db()
        h_db.record_upload(
            user_email=user_email or "guest@lumina.ai",
            session_id=target_session,
            job_id=job.job_id,
            filename=safe_filename,
            title=safe_filename,
            ingestion_mode="permanent" if is_perm else "session_only",
        )
    except Exception as e_up:
        logger.warning(f"Could not record upload in SQLite history: {e_up}")

    # Dispatch ingestion task (Celery with thread fallback)
    try:
        dispatch_ingestion_task(
            job_id=job.job_id,
            file_path=dest_path,
            scope=target_scope,
            session_id=target_session,
            source="user_upload",
        )
    except Exception as e:
        logger.error(f"Failed to dispatch ingestion task for job {job.job_id}: {e}", exc_info=True)
        job_store.update_job(
            job_id=job.job_id,
            status=IngestionJobStatus.FAILED,
            status_message=f"Dispatch failed: {e}",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Ingestion dispatch failed: {e}")

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "file_name": job.file_name,
        "scope": target_scope,
        "ingestion_mode": "permanent" if is_perm else "session_only",
        "message": f"Paper uploaded successfully. Ingestion initiated for {'permanent database' if is_perm else 'active session'}.",
    }


# ---------------------------------------------------------
# User Profile & Research History Endpoints (SQLite Persistent)
# ---------------------------------------------------------

class UserSyncRequest(BaseModel):
    email: str
    name: str
    institution: Optional[str] = None
    role: Optional[str] = None


@app.post("/api/user/sync")
async def sync_user(req: UserSyncRequest):
    """Save or update user profile details in SQLite database."""
    h_db = get_history_db()
    user_record = h_db.upsert_user(
        email=req.email,
        name=req.name,
        institution=req.institution,
        role=req.role,
    )
    return {"status": "success", "user": user_record}


@app.get("/api/user/history")
async def get_user_history(
    user_email: str = Query(..., description="User email identifier"),
    type: str = Query("all", description="'all', 'queries', or 'uploads'"),
    search: Optional[str] = Query(None, description="Search term in questions, answers, or paper titles"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Retrieve chronologically ordered research and upload history for a user."""
    h_db = get_history_db()
    items = h_db.get_user_history(
        user_email=user_email,
        item_type=type,
        query_search=search,
        limit=limit,
        offset=offset,
    )
    stats = h_db.get_user_stats(user_email=user_email)
    return {
        "user_email": user_email,
        "total_items": len(items),
        "items": items,
        "stats": stats,
    }


@app.get("/api/user/history/{history_id}")
async def get_history_item(
    history_id: str,
    user_email: Optional[str] = Query(None),
):
    """Retrieve full detail, sources, and verbatim citations for a specific history record."""
    h_db = get_history_db()
    item = h_db.get_history_item(history_id, user_email=user_email)
    if not item:
        raise HTTPException(status_code=404, detail="History record not found")
    return item


@app.delete("/api/user/history/{history_id}")
async def delete_history_item(
    history_id: str,
    user_email: str = Query(..., description="User email for verification"),
):
    """Delete an individual query or upload history item."""
    h_db = get_history_db()
    success = h_db.delete_history_item(history_id, user_email=user_email)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found or already deleted")
    return {"status": "deleted", "id": history_id}


@app.delete("/api/user/history")
async def clear_user_history(
    user_email: str = Query(..., description="User email for verification"),
    type: str = Query("all", description="'all', 'queries', or 'uploads'"),
):
    """Clear all research history entries for the specified user."""
    h_db = get_history_db()
    h_db.clear_user_history(user_email=user_email, item_type=type)
    return {"status": "cleared", "user_email": user_email, "type": type}


@app.get("/api/user/stats")
async def get_user_stats(
    user_email: str = Query(..., description="User email identifier"),
):
    """Retrieve personal research metrics, citations generated, and evidence state distribution."""
    h_db = get_history_db()
    return h_db.get_user_stats(user_email=user_email)


@app.post("/api/papers/search-online")
async def search_online_papers(req: SearchOnlineApiRequest):
    """Search for relevant papers across arXiv and Semantic Scholar."""
    discovery = get_discovery_service()
    try:
        candidates = discovery.search(
            query=req.query,
            max_results=req.max_results or 5,
            provider_name=req.provider or "all",
        )
        return {
            "query": req.query,
            "provider": req.provider,
            "candidates_count": len(candidates),
            "candidates": [c.model_dump() for c in candidates],
        }
    except Exception as e:
        logger.exception("Error searching online papers")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/papers/ingest-online")
async def ingest_online_papers(req: IngestOnlineApiRequest):
    """Download and ingest explicitly user-approved online paper candidates."""
    if not req.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided for ingestion.")

    discovery = get_discovery_service()
    job_store = get_job_store()
    online_dir = settings.online_papers_path
    online_dir.mkdir(parents=True, exist_ok=True)

    is_perm = (req.ingestion_mode or "permanent").lower() in ("permanent", "database", "global")
    target_scope = "global" if is_perm else "user"
    scope_enum = KnowledgeScope.GLOBAL if is_perm else KnowledgeScope.USER_PAPERS
    target_session = None if is_perm else (req.session_id or "default_user")

    created_jobs = []

    for candidate in req.candidates:
        # Check if already present in jobs or corpus
        cand_id = candidate.id or candidate.candidate_id
        src_provider = candidate.source_provider or candidate.source or "online"
        clean_title = "".join(c for c in candidate.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        filename = f"{clean_title[:60]}_{cand_id[-8:]}.pdf".replace(" ", "_")
        target_path = online_dir / filename

        try:
            target_path = discovery.download_candidate(candidate, target_dir=online_dir)
            filename = target_path.name
        except Exception as e:
            if not target_path.exists():
                logger.warning(f"Failed to download online paper '{candidate.title}': {e}")
                continue

        job = job_store.create_job(
            file_path=str(target_path),
            file_name=filename,
            session_id=target_session,
            scope=scope_enum,
            source=f"online_{src_provider}",
        )

        dispatch_ingestion_task(
            job_id=job.job_id,
            file_path=target_path,
            scope=target_scope,
            session_id=target_session,
            source=f"online_{candidate.source_provider}",
        )
        created_jobs.append({
            "job_id": job.job_id,
            "title": candidate.title,
            "file_name": filename,
            "status": job.status.value,
            "scope": target_scope,
            "ingestion_mode": "permanent" if is_perm else "session_only",
        })

    return {
        "message": f"Successfully initiated ingestion for {len(created_jobs)} paper(s).",
        "jobs": created_jobs,
    }


@app.get("/api/ingestion/{job_id}")
async def get_ingestion_status(job_id: str):
    """Poll ingestion job status and progress."""
    job_store = get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return job.model_dump()


@app.get("/api/ingestion")
async def list_ingestion_jobs(session_id: Optional[str] = None):
    """List recent ingestion jobs, optionally filtered by session."""
    job_store = get_job_store()
    if session_id:
        jobs = job_store.get_session_jobs(session_id)
    else:
        jobs = job_store.get_all_jobs()
    return [j.model_dump() for j in jobs]


@app.get("/api/papers")
async def list_papers(session_id: Optional[str] = None):
    """List all available research papers from both baseline corpus and user sessions."""
    catalog = get_catalog()
    papers = []

    # 1. Baseline papers (permanent corpus)
    for pid, meta in catalog.items():
        if meta.get("scope") in ("user", "user_papers"):
            continue
        papers.append({
            "paper_id": pid,
            "title": meta.get("title", pid),
            "filename": meta.get("filename", ""),
            "category": meta.get("category", "General"),
            "total_pages": meta.get("total_pages", 0),
            "total_chunks": meta.get("total_chunks", 0),
            "year": meta.get("year"),
            "scope": "global",
            "source": "baseline_corpus",
            "is_user_uploaded": False,
        })

    # 2. Dynamic ingested papers from jobs / session store
    job_store = get_job_store()
    all_jobs = job_store.get_all_jobs()
    seen_session_pids = set()
    for job in all_jobs:
        if job.status == IngestionJobStatus.COMPLETED and job.paper_id:
            if session_id and job.session_id and job.session_id != session_id:
                continue
            if job.paper_id in seen_session_pids:
                continue
            seen_session_pids.add(job.paper_id)
            papers.append({
                "paper_id": job.paper_id,
                "title": job.title or job.file_name.replace(".pdf", "").replace("_", " "),
                "filename": job.file_name,
                "category": "User Uploaded" if "user" in job.source else "Online Research",
                "total_pages": job.total_pages or 0,
                "total_chunks": job.chunk_count or job.total_chunks or 0,
                "year": 2026,
                "scope": job.scope,
                "source": job.source,
                "is_user_uploaded": True,
                "session_id": job.session_id,
            })

    return {
        "total_papers": len(papers),
        "papers": papers,
    }


@app.get("/api/papers/{paper_id}/pdf")
async def serve_paper_pdf(paper_id: str):
    """Serve the PDF file for a paper for inline viewer rendering."""
    # 1. Search in dynamic jobs
    job_store = get_job_store()
    for job in job_store.get_all_jobs():
        if job.paper_id == paper_id:
            p = Path(job.file_path)
            if p.exists():
                return FileResponse(
                    str(p),
                    media_type="application/pdf",
                    filename=job.file_name,
                    headers={"Content-Disposition": f"inline; filename={job.file_name}"},
                )

    # 2. Search in baseline catalog
    catalog = get_catalog()
    if paper_id in catalog:
        fpath = catalog[paper_id].get("file_path")
        if fpath:
            p = Path(fpath)
            if p.exists():
                return FileResponse(
                    str(p),
                    media_type="application/pdf",
                    filename=catalog[paper_id].get("filename", f"{paper_id}.pdf"),
                    headers={"Content-Disposition": f"inline; filename={catalog[paper_id].get('filename', f'{paper_id}.pdf')}"},
                )

    # 3. Fallback search across known paper storage roots
    search_dirs = [
        settings.user_upload_path,
        settings.online_papers_path,
        settings.PROJECT_ROOT / "AI_Research_Dataset",
    ]
    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for pdf_file in s_dir.rglob("*.pdf"):
            if paper_id in pdf_file.name or paper_id in pdf_file.stem:
                return FileResponse(
                    str(pdf_file),
                    media_type="application/pdf",
                    filename=pdf_file.name,
                    headers={"Content-Disposition": f"inline; filename={pdf_file.name}"},
                )

    raise HTTPException(status_code=404, detail=f"PDF for paper '{paper_id}' not found.")


# ---------------------------------------------------------
# Static Frontend Mount
# ---------------------------------------------------------

frontend_dist = settings.PROJECT_ROOT / "frontend" / "dist"
web_dir = Path(__file__).resolve().parent.parent / "web"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
elif web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

