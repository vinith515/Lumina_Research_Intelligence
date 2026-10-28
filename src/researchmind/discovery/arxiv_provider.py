"""arXiv research discovery provider utilizing the public arXiv Atom API."""

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
import requests

from researchmind.discovery.base import ResearchSourceProvider, OnlinePaperCandidate

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivProvider(ResearchSourceProvider):
    """Integrates arXiv API for scientific paper discovery and PDF retrieval."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ResearchMind/2.0 (Academic Research Assistant; mailto:researchmind@example.edu)"
        })

    def search(self, query: str, limit: int = 5) -> List[OnlinePaperCandidate]:
        """Search arXiv manuscripts matching query terms, supporting natural language questions."""
        from researchmind.discovery.base import extract_academic_search_keywords

        # Extract high-relevance academic keywords if natural language query
        keywords = extract_academic_search_keywords(query)
        effective_query = keywords if keywords else query
        clean_q = re.sub(r"[^\w\s-]", " ", effective_query).strip()

        words = clean_q.split()
        if len(words) > 1:
            # Query arXiv with all:term combinations without double-urlencoding
            query_expr = " AND ".join(f"all:{w}" for w in words[:6])
        elif words:
            query_expr = f"all:{words[0]}"
        else:
            query_expr = "all:machine learning"

        params = {
            "search_query": query_expr,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            resp = self.session.get(ARXIV_API_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            results = self._parse_feed(resp.text)
            if results:
                return results

            # Fallback if strict AND yielded no papers: try loose search
            if len(words) > 1:
                params["search_query"] = f"all:{' '.join(words[:4])}"
                resp = self.session.get(ARXIV_API_URL, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return self._parse_feed(resp.text)
            return []
        except Exception as e:
            logger.warning(f"arXiv search request failed for query '{query}': {e}")
            return []

    def _parse_feed(self, xml_text: str) -> List[OnlinePaperCandidate]:
        candidates: List[OnlinePaperCandidate] = []
        try:
            root = ET.fromstring(xml_text)
            entries = root.findall("atom:entry", ATOM_NS)

            for rank, entry in enumerate(entries, start=1):
                id_elem = entry.find("atom:id", ATOM_NS)
                title_elem = entry.find("atom:title", ATOM_NS)
                summary_elem = entry.find("atom:summary", ATOM_NS)
                published_elem = entry.find("atom:published", ATOM_NS)

                if id_elem is None or not id_elem.text or title_elem is None:
                    continue

                full_id = id_elem.text.strip()
                # arXiv ID from e.g. http://arxiv.org/abs/1706.03762v5
                match = re.search(r"arxiv\.org/abs/([0-9\.]+(?:v[0-9]+)?)", full_id)
                arxiv_id = match.group(1) if match else full_id.split("/")[-1]
                # Strip version for canonical identifier
                base_arxiv_id = re.sub(r"v[0-9]+$", "", arxiv_id)

                title = re.sub(r"\s+", " ", title_elem.text or "").strip()
                abstract = re.sub(r"\s+", " ", summary_elem.text or "").strip() if summary_elem is not None else None

                year = None
                if published_elem is not None and published_elem.text:
                    try:
                        year = int(published_elem.text[:4])
                    except ValueError:
                        pass

                authors = []
                for author_elem in entry.findall("atom:author", ATOM_NS):
                    name_elem = author_elem.find("atom:name", ATOM_NS)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())

                # Find PDF link
                pdf_url = f"https://arxiv.org/pdf/{base_arxiv_id}.pdf"
                for link in entry.findall("atom:link", ATOM_NS):
                    if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                        pdf_url = link.get("href", pdf_url)
                        if pdf_url.startswith("http://"):
                            pdf_url = "https://" + pdf_url[7:]
                        break

                doi_elem = entry.find("arxiv:doi", ATOM_NS)
                doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

                candidate = OnlinePaperCandidate(
                    candidate_id=f"arxiv_{base_arxiv_id.replace('.', '_')}",
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    source="arxiv",
                    identifier=base_arxiv_id,
                    arxiv_id=base_arxiv_id,
                    doi=doi,
                    paper_url=f"https://arxiv.org/abs/{base_arxiv_id}",
                    pdf_url=pdf_url,
                    rank=rank,
                )
                candidates.append(candidate)
        except Exception as e:
            logger.error(f"Failed to parse arXiv Atom XML response: {e}")

        return candidates

    def get_paper_metadata(self, identifier: str) -> Optional[OnlinePaperCandidate]:
        """Fetch metadata for a specific arXiv ID."""
        clean_id = re.sub(r"[^\w\.]", "", identifier)
        params = {"id_list": clean_id}
        try:
            resp = self.session.get(ARXIV_API_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            candidates = self._parse_feed(resp.text)
            return candidates[0] if candidates else None
        except Exception as e:
            logger.warning(f"Failed to retrieve arXiv paper {identifier}: {e}")
            return None

    def supports_pdf(self, candidate: OnlinePaperCandidate) -> bool:
        return bool(candidate.pdf_url)

    def download_pdf(self, candidate: OnlinePaperCandidate, target_path: Path) -> Path:
        """Download paper PDF with chunked streaming."""
        if not candidate.pdf_url:
            raise ValueError(f"No PDF URL available for candidate {candidate.candidate_id}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading arXiv PDF from {candidate.pdf_url} to {target_path}...")

        resp = self.session.get(candidate.pdf_url, stream=True, timeout=self.timeout * 2)
        resp.raise_for_status()

        # Validate that response is actually a PDF
        content_type = resp.headers.get("Content-Type", "").lower()
        if "html" in content_type and "pdf" not in content_type:
            raise ValueError(f"Server returned HTML instead of PDF from {candidate.pdf_url}")

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Validate minimal PDF magic header '%PDF'
        with open(target_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF"):
                target_path.unlink(missing_ok=True)
                raise ValueError("Downloaded file lacks standard %PDF header.")

        logger.info(f"Successfully downloaded PDF to {target_path} ({target_path.stat().st_size} bytes)")
        return target_path
