"""End-to-end ingestion pipeline with incremental processing and status tracking."""

import os
import json
import logging
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from tqdm import tqdm

from researchmind.schemas.models import DocumentElement, PaperMetadata, ResearchChunk, IngestionJobStatus
from researchmind.ingestion.unstructured_parser import UnstructuredPDFParser
from researchmind.ingestion.cleaner import DocumentCleaner
from researchmind.ingestion.metadata import AcademicMetadataExtractor
from researchmind.chunking.research_chunker import ResearchPaperChunker
from researchmind.embeddings.embedder import ResearchEmbedder
from researchmind.indexing.vector_index import VectorIndexManager
from researchmind.indexing.bm25_index import BM25IndexManager
from researchmind.config import settings

logger = logging.getLogger(__name__)


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


class IngestionPipeline:
    """Orchestrates PDF discovery, deduplication, Unstructured extraction, cleaning, and metadata persistence."""

    def __init__(
        self,
        parser: Optional[UnstructuredPDFParser] = None,
        cleaner: Optional[DocumentCleaner] = None,
        metadata_extractor: Optional[AcademicMetadataExtractor] = None,
    ):
        self.parser = parser or UnstructuredPDFParser()
        self.cleaner = cleaner or DocumentCleaner()
        self.metadata_extractor = metadata_extractor or AcademicMetadataExtractor()
        settings.ensure_directories()

        self.catalog_file = settings.metadata_path / "catalog.json"
        self.status_file = settings.metadata_path / "ingestion_status.json"
        self.catalog: Dict[str, Dict[str, Any]] = self._load_json(self.catalog_file)
        self.status: Dict[str, Dict[str, Any]] = self._load_json(self.status_file)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {path}: {e}. Initializing empty dict.")
        return {}

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_elements(self, paper_id: str, elements: List[DocumentElement]) -> Path:
        """Persist extracted and cleaned elements to a JSONL file."""
        out_file = settings.elements_dir / f"{paper_id}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for elem in elements:
                f.write(elem.model_dump_json() + "\n")
        return out_file

    def load_elements(self, paper_id: str) -> List[DocumentElement]:
        """Load extracted elements from a JSONL file."""
        file_path = settings.elements_dir / f"{paper_id}.jsonl"
        if not file_path.exists():
            raise FileNotFoundError(f"Elements file not found for paper_id: {paper_id}")
        
        elements: List[DocumentElement] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    elements.append(DocumentElement.model_validate_json(line))
        return elements

    def ingest_paper(
        self,
        pdf_path: Path,
        paper_id: Optional[str] = None,
        category: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Optional[PaperMetadata], Optional[List[DocumentElement]], str]:
        """Ingest a single research paper PDF through parsing, cleaning, and metadata extraction.
        
        Returns:
            Tuple of (PaperMetadata or None, List[DocumentElement] or None, status_str).
        """
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            return None, None, "not_found"

        file_hash = compute_sha256(pdf_path)
        cat = category or pdf_path.parent.name
        pid = paper_id or f"paper_{file_hash[:12]}"

        # Check if already processed (and not force)
        if not force and file_hash in self.status:
            existing_record = self.status[file_hash]
            if existing_record.get("status") == "processed":
                elem_file = settings.elements_dir / f"{existing_record['paper_id']}.jsonl"
                if elem_file.exists():
                    logger.debug(f"Paper {pdf_path.name} already processed as {existing_record['paper_id']}. Skipping.")
                    return PaperMetadata.model_validate(self.catalog.get(existing_record["paper_id"], {})), None, "already_processed"

        # Check if duplicate of another file
        known_hashes = {v["file_hash"]: k for k, v in self.catalog.items() if "file_hash" in v}
        if not force and file_hash in known_hashes and known_hashes[file_hash] != pid:
            orig_pid = known_hashes[file_hash]
            logger.info(f"Duplicate detected: {pdf_path.name} has identical hash to {orig_pid}. Skipping duplicate ingestion.")
            self.status[file_hash] = {
                "paper_id": orig_pid,
                "filename": pdf_path.name,
                "file_path": str(pdf_path),
                "file_hash": file_hash,
                "status": "duplicate",
                "duplicate_of": orig_pid,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_json(self.status_file, self.status)
            return None, None, "duplicate"

        try:
            # 1. Unstructured parsing
            raw_elements = self.parser.parse(pdf_path, paper_id=pid)
            if not raw_elements:
                raise ValueError("No elements extracted from PDF")

            # 2. Document cleaning
            cleaned_elements = self.clean_cleaner_elements = self.cleaner.clean_elements(raw_elements)

            # 3. Metadata extraction and section hierarchy enrichment
            paper_meta, enriched_elements = self.metadata_extractor.extract_paper_metadata(
                pdf_path=pdf_path,
                paper_id=pid,
                file_hash=file_hash,
                elements=cleaned_elements,
                category=cat,
            )

            # 4. Save elements to disk (JSONL)
            self.save_elements(pid, enriched_elements)

            # 5. Update catalog & status
            paper_meta_dict = paper_meta.model_dump()
            paper_meta_dict["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.catalog[pid] = paper_meta_dict
            self.status[file_hash] = {
                "paper_id": pid,
                "filename": pdf_path.name,
                "file_path": str(pdf_path),
                "file_hash": file_hash,
                "status": "processed",
                "total_pages": paper_meta.total_pages,
                "total_elements": len(enriched_elements),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            self._save_json(self.catalog_file, self.catalog)
            self._save_json(self.status_file, self.status)

            return paper_meta, enriched_elements, "processed"

        except Exception as e:
            logger.error(f"Failed to ingest {pdf_path.name}: {e}")
            self.status[file_hash] = {
                "paper_id": pid,
                "filename": pdf_path.name,
                "file_path": str(pdf_path),
                "file_hash": file_hash,
                "status": "failed",
                "error_message": str(e),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_json(self.status_file, self.status)
            return None, None, f"failed: {e}"

    def ingest_dataset(
        self,
        data_dir: Path,
        limit: Optional[int] = None,
        force: bool = False,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Ingest all or a sample of PDFs in the dataset directory with progress tracking."""
        pdf_files: List[Tuple[Path, str]] = []
        for root, dirs, files in os.walk(data_dir):
            cat = Path(root).name if root != str(data_dir) else "General"
            if categories and cat not in categories:
                continue
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdf_files.append((Path(root) / f, cat))

        total_discovered = len(pdf_files)
        if limit:
            pdf_files = pdf_files[:limit]

        logger.info(f"Starting ingestion of {len(pdf_files)} papers (total discovered: {total_discovered})...")

        stats = {
            "total_discovered": total_discovered,
            "targeted": len(pdf_files),
            "processed": 0,
            "already_processed": 0,
            "duplicates": 0,
            "failed": 0,
            "total_pages": 0,
            "total_elements": 0,
            "failed_files": [],
            "processed_papers": [],
        }

        with tqdm(total=len(pdf_files), desc="Ingesting Papers", unit="paper") as pbar:
            for pdf_path, cat in pdf_files:
                meta, elems, status = self.ingest_paper(pdf_path, category=cat, force=force)
                if status == "processed" and meta and elems:
                    stats["processed"] += 1
                    stats["total_pages"] += meta.total_pages
                    stats["total_elements"] += len(elems)
                    stats["processed_papers"].append({
                        "paper_id": meta.paper_id,
                        "title": meta.title,
                        "pages": meta.total_pages,
                        "elements": len(elems),
                        "category": cat,
                    })
                elif status == "already_processed":
                    stats["already_processed"] += 1
                elif status == "duplicate":
                    stats["duplicates"] += 1
                else:
                    stats["failed"] += 1
                    stats["failed_files"].append({"path": str(pdf_path), "status": status})

                pbar.update(1)

        return stats

    def ingest_and_index_paper(
        self,
        pdf_path: Path,
        paper_id: Optional[str] = None,
        category: Optional[str] = None,
        scope: str = "global",
        session_id: Optional[str] = None,
        source: str = "user_upload",
        extra_meta: Optional[Dict[str, Any]] = None,
        force: bool = False,
        progress_cb: Optional[Any] = None,
    ) -> Tuple[Optional[PaperMetadata], List[ResearchChunk], str]:
        """Unified, incremental single-paper pipeline: parse, clean, extract metadata, chunk, embed, and index into ChromaDB & BM25.
        
        Args:
            pdf_path: Path to PDF manuscript.
            paper_id: Optional custom identifier.
            category: Domain category.
            scope: Knowledge scope ('global' or 'user').
            session_id: User session ID for user-uploaded papers.
            source: Source origin ('user_upload', 'arxiv', 'semantic_scholar', 'corpus').
            extra_meta: Optional additional metadata (doi, arxiv_id, abstract, etc.).
            force: Force re-processing even if hash exists.
            progress_cb: Callable(status, percent, message) for status updates.
            
        Returns:
            Tuple of (PaperMetadata or None, List[ResearchChunk], status_message).
        """
        def report_progress(st: IngestionJobStatus, pct: int, msg: str):
            if progress_cb and callable(progress_cb):
                try:
                    progress_cb(st, pct, msg)
                except Exception as ex:
                    logger.debug(f"Progress callback exception: {ex}")

        report_progress(IngestionJobStatus.PARSING, 15, f"Parsing document layout with Unstructured.io: {pdf_path.name}")

        # Step 1-3: Parse, Clean, Extract Metadata
        meta, elements, status = self.ingest_paper(pdf_path, paper_id=paper_id, category=category, force=force)

        is_session_mode = (scope == "user" or scope == "user_papers" or bool(session_id))

        if status == "duplicate":
            file_hash = compute_sha256(pdf_path)
            orig_pid = self.status.get(file_hash, {}).get("duplicate_of") or self.status.get(file_hash, {}).get("paper_id")
            existing_meta = self.catalog.get(orig_pid)
            loaded_meta = PaperMetadata.model_validate(existing_meta) if existing_meta else None
            # Check if existing chunks can be loaded
            existing_chunks: List[ResearchChunk] = []
            chunk_file = settings.chunks_dir / f"{orig_pid}.jsonl"
            if chunk_file.exists():
                with open(chunk_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            existing_chunks.append(ResearchChunk.model_validate_json(line))

            if is_session_mode and existing_chunks:
                # Re-tag and index into dedicated temporary session database
                report_progress(IngestionJobStatus.INDEXING, 75, f"Indexing existing elements into temporary session database...")
                session_chunks = []
                for c in existing_chunks:
                    c_copy = c.model_copy(deep=True)
                    c_copy.scope = "user"
                    c_copy.session_id = session_id
                    c_copy.source = source
                    session_chunks.append(c_copy)
                embedder = ResearchEmbedder()
                embeddings = embedder.embed_texts([c.text for c in session_chunks])
                vector_mgr = VectorIndexManager()
                vector_mgr.add_chunks(session_chunks, embeddings, is_session=True)
                bm25_mgr = BM25IndexManager()
                bm25_mgr.add_chunks(session_chunks)
                report_progress(IngestionJobStatus.COMPLETED, 100, f"Indexed {len(session_chunks)} chunks into temporary session database.")
                return loaded_meta, session_chunks, "completed"

            report_progress(IngestionJobStatus.COMPLETED, 100, f"Identified duplicate of existing paper {orig_pid}. Reusing existing index.")
            return loaded_meta, existing_chunks, "duplicate"

        if status == "already_processed" and meta:
            chunk_file = settings.chunks_dir / f"{meta.paper_id}.jsonl"
            existing_chunks = []
            if chunk_file.exists():
                with open(chunk_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            existing_chunks.append(ResearchChunk.model_validate_json(line))

            if is_session_mode and existing_chunks:
                # User chose session-only upload: index into temporary session database
                report_progress(IngestionJobStatus.INDEXING, 75, f"Indexing into temporary session database for active workspace...")
                session_chunks = []
                for c in existing_chunks:
                    c_copy = c.model_copy(deep=True)
                    c_copy.scope = "user"
                    c_copy.session_id = session_id
                    c_copy.source = source
                    session_chunks.append(c_copy)
                embedder = ResearchEmbedder()
                embeddings = embedder.embed_texts([c.text for c in session_chunks])
                vector_mgr = VectorIndexManager()
                vector_mgr.add_chunks(session_chunks, embeddings, is_session=True)
                bm25_mgr = BM25IndexManager()
                bm25_mgr.add_chunks(session_chunks)
                report_progress(IngestionJobStatus.COMPLETED, 100, f"Paper indexed into temporary session database ({len(session_chunks)} chunks).")
                return meta, session_chunks, "completed"

            report_progress(IngestionJobStatus.COMPLETED, 100, f"Paper {meta.paper_id} already indexed ({len(existing_chunks)} chunks).")
            return meta, existing_chunks, "already_processed"

        if not meta or not elements:
            report_progress(IngestionJobStatus.FAILED, 0, f"Parsing failed for {pdf_path.name}")
            return None, [], f"parsing_failed: {status}"

        # Enrich metadata with scope, session, source, and extra_meta
        meta.scope = scope
        meta.session_id = session_id
        meta.source = source
        if extra_meta:
            for k, v in extra_meta.items():
                if hasattr(meta, k) and v is not None:
                    setattr(meta, k, v)

        # Step 4: Section-bounded structure-aware chunking
        report_progress(IngestionJobStatus.CHUNKING, 45, f"Structuring sections into chunks: {meta.title[:40]}...")
        chunker = ResearchPaperChunker()
        chunks = chunker.chunk_paper(paper_id=meta.paper_id, elements=elements, metadata=meta)
        if not chunks:
            report_progress(IngestionJobStatus.FAILED, 0, "No chunks generated from document elements")
            return None, [], "chunking_failed: 0 chunks"

        # Save chunks to disk
        chunk_file = settings.chunks_dir / f"{meta.paper_id}.jsonl"
        with open(chunk_file, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(c.model_dump_json() + "\n")
        meta.total_chunks = len(chunks)

        # Step 5: Dense Embeddings
        report_progress(IngestionJobStatus.EMBEDDING, 70, f"Generating dense BGE embeddings for {len(chunks)} chunks...")
        embedder = ResearchEmbedder()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_documents(chunk_texts)

        # Step 6: Incremental Vector and Sparse Indexing
        db_label = "temporary session database" if is_session_mode else "ChromaDB permanent corpus"
        report_progress(IngestionJobStatus.INDEXING, 90, f"Indexing into {db_label} and BM25Plus sparse index...")
        vector_mgr = VectorIndexManager()
        vector_mgr.add_chunks(chunks, embeddings, is_session=is_session_mode)

        bm25_mgr = BM25IndexManager()
        bm25_mgr.add_chunks(chunks)

        meta.status = "processed"
        meta.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")

        # Only update permanent catalog if permanent database was selected
        if not is_session_mode:
            self.catalog[meta.paper_id] = meta.model_dump()
            self._save_json(self.catalog_file, self.catalog)

        success_msg = f"Successfully indexed {len(chunks)} chunks into {'temporary session database' if is_session_mode else 'permanent database'}."
        report_progress(IngestionJobStatus.COMPLETED, 100, success_msg)
        logger.info(f"Successfully ingested and indexed paper {meta.paper_id} ({meta.title[:40]}) [session={is_session_mode}]")
        return meta, chunks, "completed"
