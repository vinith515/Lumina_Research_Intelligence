"""Persistent Ingestion Job store for tracking asynchronous Celery and background pipeline progress."""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from researchmind.schemas.models import IngestionJob, IngestionJobStatus
from researchmind.config import settings

logger = logging.getLogger(__name__)


class IngestionJobStore:
    """Manages lifecycle status records for PDF ingestion and indexing tasks."""

    _instance: Optional["IngestionJobStore"] = None

    def __init__(self, store_path: Optional[Path] = None):
        import threading
        self._lock = threading.Lock()
        self.store_path = store_path or (settings.metadata_path / "ingestion_jobs.json")
        self.jobs: Dict[str, Dict[str, Any]] = self._load()

    @classmethod
    def get_instance(cls, store_path: Optional[Path] = None) -> "IngestionJobStore":
        if cls._instance is None:
            cls._instance = cls(store_path)
        return cls._instance

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read {self.store_path}: {e}")
        return {}

    def _reload(self) -> None:
        """Synchronize in-memory jobs with disk store."""
        with self._lock:
            disk_jobs = self._load()
            self.jobs.update(disk_jobs)

    def _save(self) -> None:
        with self._lock:
            try:
                self.store_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.store_path, "w", encoding="utf-8") as f:
                    json.dump(self.jobs, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to persist {self.store_path}: {e}")

    def create_job(
        self,
        job_id: Optional[str] = None,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        source: str = "user_upload",
        scope: Any = "user",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_temporary: bool = False,
    ) -> IngestionJob:
        """Create and persist a new queued ingestion job."""
        final_job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        fname = file_name or filename or (Path(file_path).name if file_path else "document.pdf")
        scope_str = scope.value if hasattr(scope, "value") else str(scope)

        job = IngestionJob(
            job_id=final_job_id,
            title=title or fname or "Pending Research Manuscript",
            filename=fname,
            file_name=fname,
            file_path=file_path,
            source=source,
            scope=scope_str,
            session_id=session_id,
            status=IngestionJobStatus.PENDING,
            progress_percent=0,
            progress_pct=0.0,
            status_message="Queued for processing",
            current_stage="PENDING",
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        self.jobs[final_job_id] = job.model_dump()
        self._save()
        logger.info(f"Created ingestion job {final_job_id} for file '{fname}' (source: {source})")
        return job

    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """Retrieve job record by ID."""
        self._reload()
        data = self.jobs.get(job_id)
        if data:
            return IngestionJob.model_validate(data)
        return None

    def update_job(
        self,
        job_id: str,
        status: IngestionJobStatus,
        progress_pct: Optional[float] = None,
        progress_percent: Optional[int] = None,
        current_stage: Optional[str] = None,
        status_message: Optional[str] = None,
        chunk_count: Optional[int] = None,
        total_chunks: Optional[int] = None,
        paper_id: Optional[str] = None,
        title: Optional[str] = None,
        total_pages: Optional[int] = None,
        error: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[IngestionJob]:
        """Update job progress and state."""
        self._reload()
        if job_id not in self.jobs:
            logger.warning(f"Cannot update non-existent job {job_id}")
            return None

        record = self.jobs[job_id]
        record["status"] = status.value if hasattr(status, "value") else str(status)

        pct = progress_pct if progress_pct is not None else (progress_percent if progress_percent is not None else 0.0)
        record["progress_pct"] = float(pct)
        record["progress_percent"] = int(pct)

        msg = current_stage or status_message or record.get("status_message", "Processing")
        record["status_message"] = msg
        record["current_stage"] = msg
        record["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if paper_id:
            record["paper_id"] = paper_id
        if title:
            record["title"] = title
        if total_pages is not None:
            record["total_pages"] = total_pages

        chunks = chunk_count if chunk_count is not None else total_chunks
        if chunks is not None:
            record["total_chunks"] = chunks
            record["chunk_count"] = chunks

        err = error_message or error
        if err is not None:
            record["error"] = err
            record["error_message"] = err

        self._save()
        return IngestionJob.model_validate(record)

    def list_jobs(self, session_id: Optional[str] = None) -> List[IngestionJob]:
        """List all tracked jobs, optionally filtered by session ID."""
        self._reload()
        results = []
        for j_dict in self.jobs.values():
            job = IngestionJob.model_validate(j_dict)
            if session_id and job.session_id and job.session_id != session_id:
                continue
            results.append(job)
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    def get_all_jobs(self) -> List[IngestionJob]:
        """Return all tracked jobs."""
        return self.list_jobs(session_id=None)

    def get_session_jobs(self, session_id: str) -> List[IngestionJob]:
        """Return jobs belonging to a specific user session."""
        return self.list_jobs(session_id=session_id)


# Global singleton instance
job_store = IngestionJobStore.get_instance()
