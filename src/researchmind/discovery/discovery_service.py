"""Unified Research Discovery Service orchestrating academic providers with deduplication and local catalog matching."""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

from researchmind.discovery.base import ResearchSourceProvider, OnlinePaperCandidate
from researchmind.discovery.arxiv_provider import ArxivProvider
from researchmind.discovery.semantic_scholar_provider import SemanticScholarProvider
from researchmind.config import settings

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalize paper title for fuzzy deduplication."""
    t = re.sub(r"[^\w\s]", " ", title.lower())
    return re.sub(r"\s+", " ", t).strip()


def tokenize_title(title: str) -> set:
    """Extract significant word tokens from title or query, filtering question and generic academic stop words."""
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", title.lower())
    stop_words = {
        "the", "and", "for", "with", "via", "using", "from", "based", "towards",
        "what", "are", "how", "why", "who", "which", "when", "where", "can", "could",
        "would", "should", "will", "does", "did", "have", "has", "had", "find",
        "best", "into", "about", "against", "between", "over", "under", "after",
        "paper", "papers", "study", "research", "recent", "latest", "state", "art"
    }
    return {w for w in words if w not in stop_words}


class ResearchDiscoveryService:
    """Coordinates search across external academic providers, deduplicates candidates, and matches against local corpus."""

    def __init__(
        self,
        providers: Optional[List[ResearchSourceProvider]] = None,
        catalog_path: Optional[Path] = None,
    ):
        self.providers = providers or [ArxivProvider(), SemanticScholarProvider()]
        self.catalog_path = catalog_path or (settings.metadata_path / "catalog.json")
        self.catalog: Dict[str, Dict[str, Any]] = self._load_catalog()

    def get_provider(self, name: Optional[str]) -> Optional[ResearchSourceProvider]:
        """Look up provider by name (e.g. 'arxiv', 'semantic_scholar')."""
        if not name:
            return None
        target = name.lower()
        for p in self.providers:
            p_name = getattr(p, "provider_name", "").lower()
            p_cls = p.__class__.__name__.lower()
            if target in p_name or target in p_cls or p_name.startswith(target) or p_cls.startswith(target):
                return p
        return None

    def _load_catalog(self) -> Dict[str, Dict[str, Any]]:
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading catalog for discovery matching: {e}")
        return {}

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider_name: Optional[str] = "all",
    ) -> List[OnlinePaperCandidate]:
        """Alias for search_candidates supporting provider filtering."""
        if provider_name and provider_name != "all":
            active_providers = [
                p for p in self.providers 
                if getattr(p, "provider_name", "") == provider_name 
                or p.__class__.__name__.lower().startswith(provider_name.lower())
                or provider_name.lower() in p.__class__.__name__.lower()
            ]
            temp_service = ResearchDiscoveryService(providers=active_providers, catalog_path=self.catalog_path)
            return temp_service.search_candidates(query, limit=max_results)
        return self.search_candidates(query, limit=max_results)

    def search_candidates(self, query: str, limit: int = 5) -> List[OnlinePaperCandidate]:
        """Search all configured providers, deduplicate cross-source results, match local catalog, and rank candidates.
        
        Args:
            query: Research question or topic keywords.
            limit: Maximum number of candidate papers to return.
            
        Returns:
            Ranked list of OnlinePaperCandidate objects.
        """
        all_candidates: List[OnlinePaperCandidate] = []
        for provider in self.providers:
            try:
                results = provider.search(query, limit=limit)
                all_candidates.extend(results)
            except Exception as e:
                logger.error(f"Error querying provider {provider.__class__.__name__}: {e}")

        if not all_candidates:
            logger.info(f"No online research candidates found for query: '{query}'")
            return []

        # Step 1: Deduplicate across providers (e.g. arXiv vs Semantic Scholar copies)
        deduped = self._deduplicate_candidates(all_candidates)

        # Step 2: Check if candidates already exist in local ResearchMind corpus
        self._check_local_existence(deduped)

        # Step 3: Compute relevance score against user query
        ranked = self._rank_candidates(query, deduped)

        top_candidates = ranked[:limit]
        for idx, c in enumerate(top_candidates, start=1):
            c.rank = idx

        logger.info(f"Discovery service returned {len(top_candidates)} ranked candidates for '{query[:40]}...'")
        return top_candidates

    def _deduplicate_candidates(self, candidates: List[OnlinePaperCandidate]) -> List[OnlinePaperCandidate]:
        unique: List[OnlinePaperCandidate] = []
        seen_identifiers = set()
        seen_titles = []

        for c in candidates:
            # Check by explicit identifier
            if c.arxiv_id and c.arxiv_id in seen_identifiers:
                continue
            if c.doi and c.doi in seen_identifiers:
                continue

            # Check by title token overlap
            c_tokens = tokenize_title(c.title)
            is_dup = False
            for exist_tokens, exist_cand in seen_titles:
                if c_tokens and exist_tokens:
                    jaccard = len(c_tokens & exist_tokens) / len(c_tokens | exist_tokens)
                    if jaccard >= 0.80:
                        is_dup = True
                        # If the new candidate has a direct PDF URL and existing does not, upgrade it
                        if not exist_cand.pdf_url and c.pdf_url:
                            exist_cand.pdf_url = c.pdf_url
                        break
            if is_dup:
                continue

            if c.arxiv_id:
                seen_identifiers.add(c.arxiv_id)
            if c.doi:
                seen_identifiers.add(c.doi)
            seen_titles.append((c_tokens, c))
            unique.append(c)

        return unique

    def _check_local_existence(self, candidates: List[OnlinePaperCandidate]) -> None:
        """Flag candidates that already exist in the local ResearchMind catalog."""
        if not self.catalog:
            self.catalog = self._load_catalog()

        # Build lookup tables from local catalog
        catalog_dois = {v.get("doi"): k for k, v in self.catalog.items() if v.get("doi")}
        catalog_arxivs = {v.get("arxiv_id"): k for k, v in self.catalog.items() if v.get("arxiv_id")}
        catalog_titles = []
        for k, v in self.catalog.items():
            t = v.get("title") or ""
            if t:
                catalog_titles.append((tokenize_title(t), k))

        for c in candidates:
            # 1. DOI match
            if c.doi and c.doi in catalog_dois:
                c.already_exists_locally = True
                c.existing_paper_id = catalog_dois[c.doi]
                continue

            # 2. arXiv match
            if c.arxiv_id and c.arxiv_id in catalog_arxivs:
                c.already_exists_locally = True
                c.existing_paper_id = catalog_arxivs[c.arxiv_id]
                continue

            # 3. Fuzzy title match
            c_tokens = tokenize_title(c.title)
            if len(c_tokens) >= 3:
                for cat_tokens, pid in catalog_titles:
                    if cat_tokens:
                        jaccard = len(c_tokens & cat_tokens) / len(c_tokens | cat_tokens)
                        subset_ratio = len(c_tokens & cat_tokens) / max(1, len(c_tokens))
                        if jaccard >= 0.70 or subset_ratio >= 0.70:
                            c.already_exists_locally = True
                            c.existing_paper_id = pid
                            break

    def _rank_candidates(self, query: str, candidates: List[OnlinePaperCandidate]) -> List[OnlinePaperCandidate]:
        """Rank candidate papers based on query keyword coverage and direct PDF availability."""
        q_tokens = tokenize_title(query)

        for c in candidates:
            title_tokens = tokenize_title(c.title)
            abs_tokens = tokenize_title(c.abstract or "")

            title_overlap = len(q_tokens & title_tokens) / max(1, len(q_tokens))
            abs_overlap = len(q_tokens & abs_tokens) / max(1, len(q_tokens)) if abs_tokens else 0.0

            # Composite score: title match (weight 0.6) + abstract match (weight 0.3) + PDF availability (0.1)
            score = (title_overlap * 0.6) + (abs_overlap * 0.3)
            if c.pdf_url:
                score += 0.10
            # Small penalty if already indexed so new discoveries appear on top
            if c.already_exists_locally:
                score *= 0.85

            c.relevance_score = round(score, 4)

        # Sort descending by relevance score, with tie-breaker on publication year
        return sorted(candidates, key=lambda x: (x.relevance_score, x.year or 0), reverse=True)

    def download_candidate(self, candidate: OnlinePaperCandidate, target_dir: Optional[Path] = None) -> Path:
        """Download candidate PDF using the appropriate source provider."""
        dest_dir = target_dir or settings.online_papers_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{candidate.candidate_id}.pdf"
        target_path = dest_dir / filename

        # If already downloaded and valid
        if target_path.exists() and target_path.stat().st_size > 1000:
            with open(target_path, "rb") as f:
                if f.read(4).startswith(b"%PDF"):
                    return target_path

        # Find matching provider
        for provider in self.providers:
            if candidate.source == "arxiv" and isinstance(provider, ArxivProvider):
                return provider.download_pdf(candidate, target_path)
            elif candidate.source == "semantic_scholar" and isinstance(provider, SemanticScholarProvider):
                return provider.download_pdf(candidate, target_path)

        # Fallback to direct HTTP download if provider matching didn't catch it
        if candidate.pdf_url:
            import requests
            resp = requests.get(candidate.pdf_url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return target_path

        raise ValueError(f"No provider capable of downloading candidate {candidate.candidate_id}")
