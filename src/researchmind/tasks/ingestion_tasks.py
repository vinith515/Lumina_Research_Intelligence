"""Celery background tasks and dispatch logic for PDF ingestion and incremental indexing."""

import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from researchmind.schemas.models import IngestionJobStatus
from researchmind.tasks.celery_app import celery_app
from researchmind.tasks.job_store import job_store
from researchmind.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


def _run_ingestion_sync(
    job_id: str,
    file_path_str: str,
    scope: str = "user",
    session_id: Optional[str] = None,
    source: str = "user_upload",
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute ingestion synchronously, reporting granular progress to the job store."""
    pdf_path = Path(file_path_str)
    pipeline = IngestionPipeline()

    def progress_callback(st: IngestionJobStatus, pct: int, msg: str):
        job_store.update_job(
            job_id=job_id,
            status=st,
            progress_percent=pct,
            status_message=msg,
        )

    # Immediately report that processing has commenced
    progress_callback(
        IngestionJobStatus.PARSING,
        10,
        f"Processing document layout with Unstructured: {pdf_path.name}",
    )

    try:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF manuscript not found at {pdf_path}")

        meta, chunks, status = pipeline.ingest_and_index_paper(
            pdf_path=pdf_path,
            scope=scope,
            session_id=session_id,
            source=source,
            extra_meta=extra_meta,
            progress_cb=progress_callback,
        )

        if not meta or status.startswith("parsing_failed") or status.startswith("chunking_failed"):
            raise RuntimeError(f"Ingestion incomplete with status: {status}")

        job_store.update_job(
            job_id=job_id,
            status=IngestionJobStatus.COMPLETED,
            progress_percent=100,
            status_message=f"Ingestion and indexing complete ({len(chunks)} chunks).",
            paper_id=meta.paper_id,
            title=meta.title,
            total_pages=meta.total_pages,
            total_chunks=len(chunks),
        )

        try:
            from researchmind.database.user_history_db import UserHistoryDatabase
            UserHistoryDatabase.get_instance().update_upload_status(
                job_id=job_id,
                status="COMPLETED",
                total_pages=meta.total_pages or 1,
                total_chunks=len(chunks),
                title=meta.title,
                paper_id=meta.paper_id,
            )
        except Exception:
            pass

        return {
            "status": "success",
            "paper_id": meta.paper_id,
            "title": meta.title,
            "total_chunks": len(chunks),
        }

    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}", exc_info=True)
        job_store.update_job(
            job_id=job_id,
            status=IngestionJobStatus.FAILED,
            progress_percent=0,
            status_message=f"Failed: {str(e)}",
            error=str(e),
        )
        try:
            from researchmind.database.user_history_db import UserHistoryDatabase
            UserHistoryDatabase.get_instance().update_upload_status(
                job_id=job_id,
                status="FAILED",
            )
        except Exception:
            pass
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="researchmind.ingest_paper_task", max_retries=1)
def ingest_paper_task(
    self,
    job_id: str,
    file_path_str: str,
    scope: str = "user",
    session_id: Optional[str] = None,
    source: str = "user_upload",
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Celery task executing end-to-end PDF ingestion in a worker process."""
    return _run_ingestion_sync(
        job_id=job_id,
        file_path_str=file_path_str,
        scope=scope,
        session_id=session_id,
        source=source,
        extra_meta=extra_meta,
    )


def _is_celery_worker_active() -> bool:
    """Fast probe: check if Celery broker and workers are actively online without blocking."""
    import os
    if os.getenv("ENABLE_CELERY", "false").lower() not in ("true", "1", "yes"):
        return False
    try:
        import socket
        s = socket.socket()
        s.settimeout(0.3)
        s.connect(('localhost', 6379))
        s.close()
        workers = celery_app.control.ping(timeout=0.3)
        return bool(workers)
    except Exception:
        return False


def dispatch_ingestion_task(
    job_id: str,
    file_path: Optional[Path] = None,
    scope: str = "user",
    session_id: Optional[str] = None,
    source: str = "user_upload",
    extra_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Dispatch ingestion task to Celery/Redis queue if active, or directly in background thread."""
    if file_path is None:
        job = job_store.get_job(job_id)
        if job and job.file_path:
            file_path = Path(job.file_path)
            if hasattr(job, "scope") and job.scope:
                scope = job.scope.value if hasattr(job.scope, "value") else str(job.scope)
            if hasattr(job, "session_id") and job.session_id:
                session_id = job.session_id
            if hasattr(job, "source") and job.source:
                source = job.source
        else:
            raise ValueError(f"No file_path provided and job {job_id} not found or missing file_path")

    if _is_celery_worker_active():
        try:
            async_result = ingest_paper_task.delay(
                job_id=job_id,
                file_path_str=str(file_path),
                scope=scope,
                session_id=session_id,
                source=source,
                extra_meta=extra_meta,
            )
            logger.info(f"Dispatched job {job_id} to Celery queue (task_id: {async_result.id})")
            return str(async_result.id)
        except Exception as e:
            logger.warning(f"Failed to dispatch to Celery ({e}). Falling back to background thread.")

    # Standalone background execution: spawn background thread without blocking the HTTP request
    logger.info(f"Running ingestion job {job_id} in background worker thread.")
    t = threading.Thread(
        target=_run_ingestion_sync,
        args=(job_id, str(file_path), scope, session_id, source, extra_meta),
        daemon=True,
    )
    t.start()
    return f"thread_{job_id}"
