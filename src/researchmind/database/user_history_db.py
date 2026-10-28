"""SQLite database storage for user profiles, research queries, citations, and upload history."""

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from researchmind.config import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.metadata_path / "lumina_user_history.db"


class UserHistoryDatabase:
    """Thread-safe SQLite database manager for user activities, queries, citations, and uploads."""

    _instance: Optional["UserHistoryDatabase"] = None

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "UserHistoryDatabase":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for high concurrency
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    institution TEXT,
                    role TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS query_history (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    session_id TEXT,
                    query_text TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    evidence_state TEXT,
                    knowledge_scope TEXT,
                    retrieval_mode TEXT,
                    target_paper_title TEXT,
                    latency_ms REAL DEFAULT 0.0,
                    abstained INTEGER DEFAULT 0,
                    citations_count INTEGER DEFAULT 0,
                    citations_json TEXT DEFAULT '[]',
                    sources_json TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_query_history_user ON query_history(user_email);
                CREATE INDEX IF NOT EXISTS idx_query_history_created ON query_history(created_at DESC);

                CREATE TABLE IF NOT EXISTS upload_history (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    session_id TEXT,
                    job_id TEXT UNIQUE,
                    paper_id TEXT,
                    filename TEXT NOT NULL,
                    title TEXT NOT NULL,
                    ingestion_mode TEXT NOT NULL DEFAULT 'permanent',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    total_pages INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_upload_history_user ON upload_history(user_email);
                CREATE INDEX IF NOT EXISTS idx_upload_history_job ON upload_history(job_id);
            """)

    def upsert_user(self, email: str, name: str, institution: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
        """Insert or update user record."""
        clean_email = email.strip().lower()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,)).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE users 
                    SET name = ?, institution = COALESCE(?, institution), role = COALESCE(?, role), last_active_at = ?
                    WHERE email = ?
                    """,
                    (name.strip(), institution, role, now, clean_email),
                )
                user_id = row["id"]
            else:
                user_id = f"user_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO users (id, email, name, institution, role, created_at, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, clean_email, name.strip(), institution or "", role or "Researcher", now, now),
                )
            conn.commit()

        return {
            "id": user_id,
            "email": clean_email,
            "name": name.strip(),
            "institution": institution,
            "role": role,
        }

    def record_query(
        self,
        user_email: str,
        session_id: Optional[str],
        query_text: str,
        answer_text: str,
        evidence_state: str = "STATE_A",
        knowledge_scope: str = "global",
        retrieval_mode: str = "hybrid_rerank",
        target_paper_title: Optional[str] = None,
        latency_ms: float = 0.0,
        abstained: bool = False,
        citations: Optional[List[Dict[str, Any]]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Store a completed research query and grounded answer in history."""
        clean_email = user_email.strip().lower() if user_email else "guest@lumina.ai"
        record_id = f"hist_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        citations_list = citations or []
        sources_list = sources or []

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO query_history (
                    id, user_email, session_id, query_text, answer_text, evidence_state,
                    knowledge_scope, retrieval_mode, target_paper_title, latency_ms,
                    abstained, citations_count, citations_json, sources_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    clean_email,
                    session_id,
                    query_text,
                    answer_text,
                    evidence_state,
                    knowledge_scope,
                    retrieval_mode,
                    target_paper_title,
                    latency_ms,
                    1 if abstained else 0,
                    len(citations_list),
                    json.dumps(citations_list),
                    json.dumps(sources_list),
                    now,
                ),
            )
            conn.commit()

        return record_id

    def get_last_query_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent query record for a session."""
        if not session_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, user_email, session_id, query_text, answer_text,
                       target_paper_title, knowledge_scope, created_at
                FROM query_history
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def record_upload(
        self,
        user_email: str,
        session_id: Optional[str],
        job_id: str,
        filename: str,
        title: Optional[str] = None,
        ingestion_mode: str = "permanent",
        paper_id: Optional[str] = None,
    ) -> str:
        """Record the start of a paper upload in user history."""
        clean_email = user_email.strip().lower() if user_email else "guest@lumina.ai"
        record_id = f"up_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO upload_history (
                    id, user_email, session_id, job_id, paper_id, filename, title,
                    ingestion_mode, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    record_id,
                    clean_email,
                    session_id,
                    job_id,
                    paper_id,
                    filename,
                    title or filename,
                    ingestion_mode,
                    now,
                    now,
                ),
            )
            conn.commit()

        return record_id

    def update_upload_status(
        self,
        job_id: str,
        status: str,
        total_pages: int = 0,
        total_chunks: int = 0,
        title: Optional[str] = None,
        paper_id: Optional[str] = None,
    ) -> None:
        """Update status and metadata of an upload history item."""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            if title and paper_id:
                conn.execute(
                    """
                    UPDATE upload_history
                    SET status = ?, total_pages = ?, total_chunks = ?, title = ?, paper_id = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (status, total_pages, total_chunks, title, paper_id, now, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE upload_history
                    SET status = ?, total_pages = ?, total_chunks = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (status, total_pages, total_chunks, now, job_id),
                )
            conn.commit()

    def get_user_history(
        self,
        user_email: str,
        item_type: str = "all",
        query_search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch combined or filtered history items for the given user, ordered newest first."""
        clean_email = user_email.strip().lower()
        items: List[Dict[str, Any]] = []

        with self._get_connection() as conn:
            # 1. Query History
            if item_type in ("all", "queries", "chat"):
                sql = "SELECT * FROM query_history WHERE user_email = ?"
                params: List[Any] = [clean_email]
                if query_search:
                    sql += " AND (query_text LIKE ? OR answer_text LIKE ?)"
                    params.extend([f"%{query_search}%", f"%{query_search}%"])
                sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                rows = conn.execute(sql, params).fetchall()
                for r in rows:
                    try:
                        citations = json.loads(r["citations_json"])
                    except Exception:
                        citations = []
                    try:
                        sources = json.loads(r["sources_json"])
                    except Exception:
                        sources = []

                    items.append({
                        "id": r["id"],
                        "type": "query",
                        "user_email": r["user_email"],
                        "session_id": r["session_id"],
                        "query": r["query_text"],
                        "answer": r["answer_text"],
                        "evidence_state": r["evidence_state"],
                        "knowledge_scope": r["knowledge_scope"],
                        "retrieval_mode": r["retrieval_mode"],
                        "target_paper_title": r["target_paper_title"],
                        "latency_ms": r["latency_ms"],
                        "abstained": bool(r["abstained"]),
                        "citations_count": r["citations_count"],
                        "citations": citations,
                        "sources": sources,
                        "created_at": r["created_at"],
                    })

            # 2. Upload History
            if item_type in ("all", "uploads"):
                sql = "SELECT * FROM upload_history WHERE user_email = ?"
                params = [clean_email]
                if query_search:
                    sql += " AND (title LIKE ? OR filename LIKE ?)"
                    params.extend([f"%{query_search}%", f"%{query_search}%"])
                sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                rows = conn.execute(sql, params).fetchall()
                for r in rows:
                    items.append({
                        "id": r["id"],
                        "type": "upload",
                        "user_email": r["user_email"],
                        "session_id": r["session_id"],
                        "job_id": r["job_id"],
                        "paper_id": r["paper_id"],
                        "filename": r["filename"],
                        "title": r["title"],
                        "ingestion_mode": r["ingestion_mode"],
                        "status": r["status"],
                        "total_pages": r["total_pages"],
                        "total_chunks": r["total_chunks"],
                        "created_at": r["created_at"],
                    })

        # Sort combined stream by created_at descending
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]

    def get_history_item(self, history_id: str, user_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a specific history item with full citations & details."""
        with self._get_connection() as conn:
            # Check queries
            sql = "SELECT * FROM query_history WHERE id = ?"
            params = [history_id]
            if user_email:
                sql += " AND user_email = ?"
                params.append(user_email.strip().lower())
            row = conn.execute(sql, params).fetchone()
            if row:
                try:
                    citations = json.loads(row["citations_json"])
                except Exception:
                    citations = []
                try:
                    sources = json.loads(row["sources_json"])
                except Exception:
                    sources = []
                return {
                    "id": row["id"],
                    "type": "query",
                    "user_email": row["user_email"],
                    "session_id": row["session_id"],
                    "query": row["query_text"],
                    "answer": row["answer_text"],
                    "evidence_state": row["evidence_state"],
                    "knowledge_scope": row["knowledge_scope"],
                    "retrieval_mode": row["retrieval_mode"],
                    "target_paper_title": row["target_paper_title"],
                    "latency_ms": row["latency_ms"],
                    "abstained": bool(row["abstained"]),
                    "citations_count": row["citations_count"],
                    "citations": citations,
                    "sources": sources,
                    "created_at": row["created_at"],
                }

            # Check uploads
            sql = "SELECT * FROM upload_history WHERE id = ?"
            params = [history_id]
            if user_email:
                sql += " AND user_email = ?"
                params.append(user_email.strip().lower())
            row = conn.execute(sql, params).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "type": "upload",
                    "user_email": row["user_email"],
                    "session_id": row["session_id"],
                    "job_id": row["job_id"],
                    "paper_id": row["paper_id"],
                    "filename": row["filename"],
                    "title": row["title"],
                    "ingestion_mode": row["ingestion_mode"],
                    "status": row["status"],
                    "total_pages": row["total_pages"],
                    "total_chunks": row["total_chunks"],
                    "created_at": row["created_at"],
                }

        return None

    def delete_history_item(self, history_id: str, user_email: str) -> bool:
        """Delete an individual history record belonging to the user."""
        clean_email = user_email.strip().lower()
        with self._get_connection() as conn:
            cur1 = conn.execute("DELETE FROM query_history WHERE id = ? AND user_email = ?", (history_id, clean_email))
            cur2 = conn.execute("DELETE FROM upload_history WHERE id = ? AND user_email = ?", (history_id, clean_email))
            conn.commit()
            return (cur1.rowcount + cur2.rowcount) > 0

    def clear_user_history(self, user_email: str, item_type: str = "all") -> bool:
        """Clear all history items for the given user."""
        clean_email = user_email.strip().lower()
        with self._get_connection() as conn:
            if item_type in ("all", "queries"):
                conn.execute("DELETE FROM query_history WHERE user_email = ?", (clean_email,))
            if item_type in ("all", "uploads"):
                conn.execute("DELETE FROM upload_history WHERE user_email = ?", (clean_email,))
            conn.commit()
            return True

    def get_user_stats(self, user_email: str) -> Dict[str, Any]:
        """Aggregate intelligence stats for a particular user."""
        clean_email = user_email.strip().lower()
        with self._get_connection() as conn:
            # Queries count
            q_row = conn.execute("SELECT COUNT(*) as c FROM query_history WHERE user_email = ?", (clean_email,)).fetchone()
            total_queries = q_row["c"] if q_row else 0

            # Uploads count
            u_row = conn.execute("SELECT COUNT(*) as c FROM upload_history WHERE user_email = ?", (clean_email,)).fetchone()
            total_uploads = u_row["c"] if u_row else 0

            # Evidence states
            ev_rows = conn.execute(
                "SELECT evidence_state, COUNT(*) as c FROM query_history WHERE user_email = ? GROUP BY evidence_state",
                (clean_email,),
            ).fetchall()
            evidence_dist = {r["evidence_state"]: r["c"] for r in ev_rows}

            # Knowledge scopes used
            sc_rows = conn.execute(
                "SELECT knowledge_scope, COUNT(*) as c FROM query_history WHERE user_email = ? GROUP BY knowledge_scope",
                (clean_email,),
            ).fetchall()
            scope_dist = {r["knowledge_scope"]: r["c"] for r in sc_rows}

            # Citations generated
            c_row = conn.execute("SELECT SUM(citations_count) as c FROM query_history WHERE user_email = ?", (clean_email,)).fetchone()
            total_citations = c_row["c"] or 0 if c_row else 0

        return {
            "total_queries": total_queries,
            "total_uploads": total_uploads,
            "total_citations": total_citations,
            "evidence_distribution": {
                "STATE_A": evidence_dist.get("STATE_A", 0),
                "STATE_B": evidence_dist.get("STATE_B", 0),
                "STATE_C": evidence_dist.get("STATE_C", 0),
            },
            "scopes_distribution": scope_dist,
        }
