"""Semantic Scholar discovery provider utilizing the public Semantic Scholar Graph API."""

import logging
import re
from pathlib import Path
from typing import List, Optional
import requests

from researchmind.discovery.base import ResearchSourceProvider, OnlinePaperCandidate
from researchmind.config import settings

logger = logging.getLogger(__name__)

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"


class SemanticScholarProvider(ResearchSourceProvider):
    """Integrates Semantic Scholar Graph API for academic discovery and open-access retrieval."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        self.api_key = api_key or settings.SEMANTIC_SCHOLAR_API_KEY
        self.timeout = timeout
        self.session = requests.Session()
        headers = {
            "User-Agent": "ResearchMind/2.0 (Academic Assistant; mailto:researchmind@example.edu)"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        self.session.headers.update(headers)

    def search(self, query: str, limit: int = 5) -> List[OnlinePaperCandidate]:
        """Search Semantic Scholar papers matching research query, supporting natural language questions."""
        from researchmind.discovery.base import extract_academic_search_keywords

        keywords = extract_academic_search_keywords(query)
        effective_query = keywords if keywords else query
        clean_q = re.sub(r"[^\w\s-]", " ", effective_query).strip()

        params = {
            "query": clean_q,
            "limit": limit,
            "fields": "title,authors,year,abstract,externalIds,url,openAccessPdf",
        }

        try:
            resp = self.session.get(S2_SEARCH_URL, params=params, timeout=self.timeout)
            if resp.status_code == 429:
                logger.warning("Semantic Scholar API rate limit encountered (HTTP 429).")
                return []
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            if items:
                return self._parse_items(items)

            # Fallback to original raw clean query if extracted keywords yielded nothing
            if keywords and keywords != query:
                raw_clean = re.sub(r"[^\w\s-]", " ", query).strip()
                params["query"] = raw_clean
                resp = self.session.get(S2_SEARCH_URL, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return self._parse_items(resp.json().get("data", []))
            return []
        except Exception as e:
            logger.warning(f"Semantic Scholar search request failed for query '{query}': {e}")
            return []

    def _parse_items(self, items: List[dict]) -> List[OnlinePaperCandidate]:
        candidates: List[OnlinePaperCandidate] = []
        for rank, item in enumerate(items, start=1):
            paper_id = item.get("paperId") or ""
            title = (item.get("title") or "").strip()
            if not title:
                continue

            authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            year = item.get("year")
            abstract = item.get("abstract")
            ext_ids = item.get("externalIds") or {}
            doi = ext_ids.get("DOI")
            arxiv_id = ext_ids.get("ArXiv")

            # Determine open access PDF URL
            open_access = item.get("openAccessPdf") or {}
            pdf_url = open_access.get("url")
            if not pdf_url and arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            candidate = OnlinePaperCandidate(
                candidate_id=f"s2_{paper_id[:16]}",
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                source="semantic_scholar",
                identifier=paper_id,
                doi=doi,
                arxiv_id=arxiv_id,
                semantic_scholar_id=paper_id,
                paper_url=item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
                pdf_url=pdf_url,
                rank=rank,
            )
            candidates.append(candidate)

        return candidates

    def get_paper_metadata(self, identifier: str) -> Optional[OnlinePaperCandidate]:
        """Fetch metadata for a single Semantic Scholar paper ID."""
        url = f"{S2_PAPER_URL}/{identifier}"
        params = {"fields": "title,authors,year,abstract,externalIds,url,openAccessPdf"}
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            items = self._parse_items([resp.json()])
            return items[0] if items else None
        except Exception as e:
            logger.warning(f"Failed to fetch Semantic Scholar paper {identifier}: {e}")
            return None

    def supports_pdf(self, candidate: OnlinePaperCandidate) -> bool:
        return bool(candidate.pdf_url)

    def download_pdf(self, candidate: OnlinePaperCandidate, target_path: Path) -> Path:
        """Download open-access manuscript PDF."""
        if not candidate.pdf_url:
            raise ValueError(f"No direct PDF available for Semantic Scholar candidate {candidate.candidate_id}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading Semantic Scholar PDF from {candidate.pdf_url} to {target_path}...")

        resp = self.session.get(candidate.pdf_url, stream=True, timeout=self.timeout * 2)
        resp.raise_for_status()

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        with open(target_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF"):
                target_path.unlink(missing_ok=True)
                raise ValueError("Downloaded file is not a valid PDF manuscript.")

        logger.info(f"Successfully downloaded PDF to {target_path} ({target_path.stat().st_size} bytes)")
        return target_path
